"""
doc_translator.py
=================

Translates a Bengali (or mixed Bangla-English) document chunk into clean,
accurate English **before** it is stored in the vector database.

Pipeline step order (called from admin_panel/services.py):
    1. translate_document_to_english(text)   <- this module
    2. entity_normalizer.normalize_entities()
    3. append context_added_date / context_added_time metadata

Design decisions
----------------
- Uses the shared `get_llm()` / `call_llm()` helpers from llm_utils so the
  same Gemini model and API key are reused without a new connection.
- The system prompt is written to:
    * Preserve meaning 1-to-1 (no summarising, no paraphrasing).
    * Keep Bengali proper nouns, names, acronyms and technical terms intact
      rather than guessing a wrong English translation.
    * Return ONLY the translated text – no preamble, no explanation.
- If the LLM call fails or returns empty output the original text is returned
  unchanged so that the upload can still proceed.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make Cnpi_RAG importable when this file is used from cnpi_api/
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parent.parent   # Cnpi_RAG/
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from utils.llm_utils import call_llm   # noqa: E402

# ---------------------------------------------------------------------------
# System prompt (split into 3 configurable layers)
# ---------------------------------------------------------------------------

CORE_INSTRUCTIONS = """==================================================
LAYER 1: CORE INSTRUCTIONS (IMMUTABLE)
==================================================

ROLE:
You are a professional Bengali-to-English translation engine.

TASK:
Translate the entire input into fluent, natural English. Support Bengali Unicode, romanized Bengali (Banglish), and mixed Bengali-English text.

STRICT RULES:

1. COMPLETE TRANSLATION
Translate the entire input. Do not leave translatable Bengali or Banglish text untranslated.

2. MEANING PRESERVATION
Preserve the original meaning exactly. Never summarize, paraphrase, add, remove, or reorder information. Retain every fact and detail.

3. PROPER NOUNS AND TECHNICAL TERMS
Preserve Bengali proper nouns and names when no established English equivalent exists. Use standard romanization for names. Keep existing English technical acronyms unchanged.

4. BANGLISH RECOGNITION
Recognize common Bengali words written in English letters. Interpret them according to context rather than treating them as ordinary English words.

5. UNCERTAINTY HANDLING
Never guess. If a Bengali word or phrase has no confidently identifiable English translation, retain it in its original form within the otherwise-English translation.

6. OUTPUT FORMAT
Return ONLY the translated English text. Do not include preambles, explanations, Markdown, or quotation marks around the output.

7. NUMBERS AND DATES
Preserve numbers, dates, and phone numbers exactly as they appear in the source.

8. STRUCTURE PRESERVATION
Preserve original line breaks, bullet points, paragraphs, and numbered-item structure. Keep numbered items numbered in English."""

PROJECT_CONFIGURATION = """==================================================
LAYER 2: PROJECT CONFIGURATION (CONFIGURABLE)
==================================================

PROJECT IDENTITY:
A Bengali-to-English translation system for a Chapainawabganj polytechnic institute(CNPI).

DOMAIN:
Educational and institutional documents, communications, notices, academic information, and institute-related content.

SPECIALIZATION:
The translation engine specializes in understanding Bengali and Banglish expressions used in the Bangladeshi educational and institutional environment.

PROJECT-SPECIFIC TERMINOLOGY:
- Institute and place names must retain their established English spellings or standard romanizations.
- Educational and technical acronyms must remain unchanged.
- Preserve institution-specific terminology whenever no established English equivalent exists."""

EXAMPLES_REFERENCE = """==================================================
LAYER 3: EXAMPLES & REFERENCE (CONFIGURABLE)
==================================================

A. INPUT LANGUAGE EXAMPLES

Bengali Unicode:
আজকে ক্লাস হবে না

Banglish:
ajke class hobe na

Mixed:
আজকে class হবে না

Expected translation for all three:
There will be no class today.


B. PROPER NOUN AND ACRONYM EXAMPLES

Person name:
মোঃ রাসেল → Md. Rasel

Institute/place name:
চাঁপাইনবাবগঞ্জ → Chapainawabganj

Technical acronyms:
CST, ET, ENT, CNPI → Keep unchanged.


C. BANGLISH VOCABULARY REFERENCE

Recognize these common Bengali words and their romanized variations:

- ajke / ajk / aaj = today
- kal = tomorrow / yesterday (context-dependent)
- hobe / hbe = will be
- korbo / korbe = will do
- jabe / jabo = will go
- asbe / asbo = will come
- dao / daw = give
- koro / kro = do
- na / nai / nei = no / not
- class = class (same English word, Bengali pronunciation)
- notis = notice

Use contextual interpretation when a word has multiple possible meanings."""

_TRANSLATION_SYSTEM_PROMPT = "\n\n".join([
    CORE_INSTRUCTIONS,
    PROJECT_CONFIGURATION,
    EXAMPLES_REFERENCE,
])

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate_to_english(text: str) -> str:
    """Translate *text* from Bengali/Banglish to English.

    Parameters
    ----------
    text:
        The raw document content (can be Bengali Unicode, Banglish, or mixed).

    Returns
    -------
    str
        The English-translated content.  If translation fails or produces an
        empty result the original *text* is returned unchanged.
    """
    if not text or not text.strip():
        return text

    # Check if translation is needed (Bengali Unicode OR Banglish)
    if not _should_translate(text):
        logger.info("doc_translator: text is already in English – skipping translation.")
        return text

    user_prompt = (
        "Translate the following document text to English following the rules "
        "in the system prompt. "
        "NOTE: This text may be in Bengali Unicode, Banglish (Bengali written in English letters), or mixed. "
        "Translate all non-English content to proper English.\n\n"
        "--- BEGIN DOCUMENT ---\n"
        f"{text}\n"
        "--- END DOCUMENT ---"
    )

    try:
        translated = call_llm(_TRANSLATION_SYSTEM_PROMPT, user_prompt)
        translated = translated.strip()

        if not translated:
            logger.warning("doc_translator: LLM returned empty translation; using original text.")
            return text

        logger.info("doc_translator: Translation successful (input %d chars → output %d chars).",
                    len(text), len(translated))
        return translated

    except Exception as exc:  # noqa: BLE001
        logger.exception("doc_translator: Translation failed (%s); using original text.", exc)
        return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _contains_bengali(text: str) -> bool:
    """Return True if *text* contains at least one Bengali Unicode character."""
    return any("\u0980" <= ch <= "\u09FF" for ch in text)


def _is_banglish(text: str) -> bool:
    """Detect if text is likely Banglish (Bengali written in English letters).
    
    Banglish characteristics:
    - Uses English letters but Bengali words/grammar
    - Common patterns: "hobe", "korbo", "dekhbo", "jabe", "asbe", "dao", "koro"
    - Common endings: -e, -o, -bo, -be, -te, -le, -ge, -che, -chhe
    - Common words: ajke, amar, tumi, amra, tomar, apni, keno, kothay, kivabe
    """
    if not text or not text.strip():
        return False
    
    text_lower = text.lower()
    
    # Common Banglish words (high-confidence indicators)
    banglish_words = [
        # Time/Date
        'ajke', 'ajk', 'aaj', 'kal', 'parsu', 'agamikal', 'gatkal',
        # Pronouns
        'amar', 'tomar', 'tumi', 'apni', 'amra', 'tomra', 'tara',
        # Question words
        'keno', 'kno', 'ken', 'kothay', 'kokhon', 'kivabe', 'kibhabe', 'ki',
        # Verbs (common endings)
        'hobe', 'hbe', 'hoye', 'korbo', 'krbo', 'korbe', 'dekhbo', 'dekhbe',
        'jabe', 'jabo', 'asbe', 'asbo', 'khabo', 'khabe', 'chai', 'chao',
        # Common words
        'dao', 'daw', 'koro', 'kro', 'dekho', 'bolo', 'bol', 'shuno', 'suno',
        'ache', 'ase', 'nai', 'nay', 'kora', 'diye', 'dilo', 'holo', 'holo',
        'thake', 'thakbe', 'thakbo', 'gelo', 'giye', 'ese', 'eshe',
        # Negation
        'na', 'nah', 'nai', 'nei', 'nay',
        # Common nouns
        'class', 'notis', 'notice', 'porikha', 'porikkha', 'exam',
        'school', 'college', 'office', 'kaj', 'kaaj',
    ]
    
    # Check if any Banglish word exists in the text
    words = text_lower.split()
    for word in words:
        if word in banglish_words:
            return True
    
    # Check common Banglish verb endings (more than 2 occurrences)
    banglish_endings = ['hobe', 'hbe', 'korbo', 'korbe', 'jabe', 'jabo', 'asbe', 'dao', 'che', 'chhe']
    ending_count = sum(1 for ending in banglish_endings if ending in text_lower)
    if ending_count >= 2:
        return True
    
    return False


def _should_translate(text: str) -> bool:
    """Return True if text should be translated (Bengali or Banglish)."""
    return _contains_bengali(text) or _is_banglish(text)
