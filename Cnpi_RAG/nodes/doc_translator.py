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

1. TRANSLATE the entire input text from Bengali (or mixed Bangla-English) \
into fluent, natural English.

2. PRESERVE MEANING exactly. Do NOT summarise, paraphrase, add, remove, or \
reorder any information. The English output must carry the same facts and \
details as the original.

3. KEEP Bengali proper nouns and names intact when there is no established \
English equivalent:
   - Person names (e.g. "মোঃ রাসেল" → "Md. Rasel", use standard romanisation)
   - Institute/place names (e.g. "চাঁপাইনবাবগঞ্জ" → "Chapainawabganj")
   - Technical acronyms already in English (CST, ET, ENT, CNPI, etc.) → keep as-is

4. DO NOT GUESS.  If you are unsure of the correct English translation of a \
specific Bengali word or phrase, leave that word/phrase in Bengali as-is \
inside the otherwise-English text.  It is better to keep a Bengali word than \
to produce an incorrect English word.

5. OUTPUT FORMAT: Return ONLY the translated English text. No preamble, no \
explanation, no markdown, no quotation marks around the output.

6. NUMBERS, DATES, PHONE NUMBERS: keep exactly as they appear in the source.

7. STRUCTURE: Preserve the original line breaks, bullet points, and paragraph \
structure. If the source has numbered items, keep them numbered in English.
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate_to_english(text: str) -> str:
    """Translate *text* from Bengali (or mixed Bangla-English) to English.

    Parameters
    ----------
    text:
        The raw document content submitted via the admin panel.

    Returns
    -------
    str
        The English-translated content.  If translation fails or produces an
        empty result the original *text* is returned unchanged.
    """
    if not text or not text.strip():
        return text

    # If the text is already entirely ASCII/Latin (i.e. no Bengali Unicode
    # codepoints in the U+0980–U+09FF range), skip the LLM call entirely.
    if not _contains_bengali(text):
        logger.info("doc_translator: text has no Bengali characters – skipping translation.")
        return text

    user_prompt = (
        "Translate the following document text to English following the rules "
        "in the system prompt. Do NOT add anything extra.\n\n"
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
