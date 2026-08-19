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
# System prompt
# ---------------------------------------------------------------------------

_TRANSLATION_SYSTEM_PROMPT = """\
You are a professional Bengali-to-English translator specialising in \
educational and institutional documents for a Bangladeshi polytechnic institute.

STRICT RULES – follow every rule without exception:

1. TRANSLATE the entire input text from Bengali (Bengali Unicode, Banglish, or mixed) \
into fluent, natural English.

   - Bengali Unicode: আজকে ক্লাস হবে না
   - Banglish (romanized): ajke class hobe na
   - Mixed: আজকে class হবে না
   
   ALL must translate to: "There will be no class today."

2. PRESERVE MEANING exactly. Do NOT summarise, paraphrase, add, remove, or \
reorder any information. The English output must carry the same facts and \
details as the original.

3. KEEP Bengali proper nouns and names intact when there is no established \
English equivalent:
   - Person names (e.g. "মোঃ রাসেল" → "Md. Rasel", use standard romanisation)
   - Institute/place names (e.g. "চাঁপাইনবাবগঞ্জ" → "Chapainawabganj")
   - Technical acronyms already in English (CST, ET, ENT, CNPI, etc.) → keep as-is

4. BANGLISH DETECTION: Recognise common Bengali words written in English letters:
   - ajke/ajk/aaj = today
   - kal = tomorrow/yesterday (context-dependent)
   - hobe/hbe = will be
   - korbo/korbe = will do
   - jabe/jabo = will go
   - asbe/asbo = will come
   - dao/daw = give
   - koro/kro = do
   - na/nai/nei = no/not
   - class = class (same word but Bengali pronunciation)
   - notis = notice

5. DO NOT GUESS.  If you are unsure of the correct English translation of a \
specific Bengali word or phrase, leave that word/phrase in its original form \
inside the otherwise-English text.  It is better to keep the original word than \
to produce an incorrect English word.

6. OUTPUT FORMAT: Return ONLY the translated English text. No preamble, no \
explanation, no markdown, no quotation marks around the output.

7. NUMBERS, DATES, PHONE NUMBERS: keep exactly as they appear in the source.

8. STRUCTURE: Preserve the original line breaks, bullet points, and paragraph \
structure. If the source has numbered items, keep them numbered in English.
"""

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
