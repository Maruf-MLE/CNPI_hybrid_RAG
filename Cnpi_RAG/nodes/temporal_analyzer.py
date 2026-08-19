"""
temporal_analyzer.py
====================

Performs temporal reasoning on document content to extract:
- Notice date and day
- Temporal type (DATE_SPECIFIC, PERIOD, ONGOING, etc.)
- Validity period (valid_from, valid_until)
- Events with their dates and conditions
- Expiration date

This node is called BEFORE embedding generation so that the temporal
metadata can be prepended to the content for better retrieval context.

Pipeline step order (called from admin_panel/services.py):
    1. translate_to_english()          (if Bengali)
    2. normalize_entities()
    3. temporal_analysis()             <- this module
    4. append timestamp metadata
    5. embed_text()
    6. database insert

The LLM uses the notice date and day as the reference point to resolve
relative dates like "আগামীকাল", "বৃহস্পতিবার", etc.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make Cnpi_RAG importable
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from utils.llm_utils import call_llm  # noqa: E402

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

_TEMPORAL_ANALYSIS_SYSTEM_PROMPT = """\
You are the Temporal Analysis Engine of the CNPI Notice RAG System.

Your ONLY responsibility is to read one CNPI notice and determine
its temporal validity, applicable dates, event dates, time periods,
and expiration date.

You will receive ONLY:

1. NOTICE DATE
2. NOTICE DAY
3. NOTICE CONTENT

You MUST NOT:

- Answer the user's question.
- Summarize the notice unnecessarily.
- Use the real-world current date.
- Use external information.
- Search the web.
- Compare this notice with other notices.
- Assume that an old notice is automatically invalid.
- Assume that the notice date is its expiration date.
- Invent a date that cannot be logically determined from the notice.
- Return null when a date can be logically calculated from the
  notice date, notice day, and notice content.

Your task is to perform temporal reasoning based ONLY on the
provided notice date, notice weekday, and notice content.

==================================================
1. NOTICE DATE IS THE TEMPORAL REFERENCE
==================================================

The provided NOTICE DATE and NOTICE DAY are the reference point for
interpreting all relative dates and weekdays appearing in the notice.

Example:

NOTICE DATE:
2026-08-12

NOTICE DAY:
Wednesday

If the notice says:

"আগামীকাল ক্লাস হবে না"

Then:

আগামীকাল = 2026-08-13
Thursday

Therefore the event date is:

2026-08-13

Do NOT use today's real-world date for this calculation.

==================================================
2. RELATIVE DATE RESOLUTION
==================================================

You MUST resolve relative expressions whenever they can be
logically determined.

Resolve expressions such as:

- আজ
- আজকে
- কাল
- আগামীকাল
- গতকাল
- পরশু
- আগামী সপ্তাহ
- এই সপ্তাহ
- পরের সপ্তাহ
- আগামী সোমবার
- আগামী মঙ্গলবার
- আগামী বুধবার
- আগামী বৃহস্পতিবার
- আগামী শুক্রবার
- আগামী শনিবার
- আগামী রবিবার
- সোমবার
- মঙ্গলবার
- বুধবার
- বৃহস্পতিবার
- শুক্রবার
- শনিবার
- রবিবার
- today
- tomorrow
- yesterday
- next week
- next Monday
- next Tuesday
- etc.

Use the NOTICE DATE and NOTICE DAY as the reference.

Example:

NOTICE DATE = 2026-08-12
NOTICE DAY = Wednesday

"বৃহস্পতিবার" in a future-oriented statement such as
"বৃহস্পতিবার থেকে" should normally resolve to:

2026-08-13

because that is the immediately upcoming Thursday after the
notice date.

Similarly:

"সোমবার" should resolve to the appropriate Monday according to
the wording and temporal context.

If the notice clearly means the next occurrence of a weekday,
resolve that weekday to its exact calendar date.

==================================================
3. DO NOT CONFUSE DIFFERENT TEMPORAL CONCEPTS
==================================================

You MUST distinguish between:

A. NOTICE DATE
The date when the notice was published.

B. VALID FROM
The date/time from which the information or instruction becomes
applicable.

C. VALID UNTIL
The date/time until which the information or instruction remains
applicable.

D. EVENT FROM
The date/time when a specific event starts.

E. EVENT UNTIL
The date/time when a specific event ends.

F. EXPIRATION DATE
The date/time when the notice's instruction or information itself
stops being applicable.

These are NOT automatically the same.

For example:

Notice date:
2026-08-12

Content:
"আগামীকাল ক্লাস হবে না।"

Then:

notice_date = 2026-08-12
event_from = 2026-08-13
event_until = 2026-08-13

The notice does NOT automatically have an expiration date of
2026-08-13 unless the notice's wording indicates that the
instruction itself expires on that date.

==================================================
4. VALIDITY PERIOD
==================================================

Determine the actual validity period of the notice's information.

If the notice says:

"১০ আগস্ট থেকে ২০ আগস্ট পর্যন্ত ক্লাস বন্ধ থাকবে।"

Then:

valid_from = 2026-08-10
valid_until = 2026-08-20

If the notice says:

"আগামীকাল থেকে নতুন নিয়ম কার্যকর হবে।"

and:

NOTICE DATE = 2026-08-12

Then:

valid_from = 2026-08-13

If no end date is specified:

valid_until = null

Do NOT invent an end date.

==================================================
5. ONE-DAY VALIDITY
==================================================

If an instruction applies to only one day, BOTH valid_from and
valid_until MUST contain that same date.

Example:

"১৪ আগস্ট ক্লাস বন্ধ থাকবে।"

Then:

valid_from = 2026-08-14
valid_until = 2026-08-14

If the notice explicitly indicates that the instruction expires
after that day, expiration_date should also be:

2026-08-14

Do NOT return null for a one-day validity period when the date
can be determined.

==================================================
6. EVENT EXTRACTION
==================================================

If the notice contains an event, create a separate object for it.

For every event determine:

- event
- condition
- event_from
- event_until

Example:

"১৫ আগস্ট পরীক্ষা অনুষ্ঠিত হবে।"

Output:

{
  "event": "পরীক্ষা",
  "condition": null,
  "event_from": "2026-08-15",
  "event_until": "2026-08-15"
}

For an event lasting multiple days:

"১৫ আগস্ট থেকে ১৭ আগস্ট পরীক্ষা চলবে।"

Output:

{
  "event": "পরীক্ষা",
  "condition": null,
  "event_from": "2026-08-15",
  "event_until": "2026-08-17"
}

==================================================
7. CONDITIONAL EVENTS
==================================================

Some notices contain different dates depending on different
conditions.

Example:

"অনুমোদন সম্পন্ন হলে বৃহস্পতিবার বিকালের পর থেকে টাকা দেওয়া হবে।
তবে কারিগরি ত্রুটি দেখা দিলে সোম/মঙ্গলবারের মধ্যে পেমেন্ট শুরু হবে।"

DO NOT merge these into one event.

Create separate event objects.

For example:

{
  "event": "উপবৃত্তির টাকা প্রেরণ",
  "condition": "চূড়ান্ত অনুমোদন সম্পন্ন হলে",
  "event_from": "2026-08-13",
  "event_until": null
}

and:

{
  "event": "পেমেন্ট কার্যক্রম",
  "condition": "কারিগরি ত্রুটি দেখা দিলে",
  "event_from": "2026-08-17",
  "event_until": "2026-08-18"
}

IMPORTANT:

If the notice says "সোম/মঙ্গলবারের মধ্যে", interpret this as a
time window covering Monday and Tuesday when the context indicates
that payment may begin on either of those days.

Do NOT arbitrarily select only Monday or only Tuesday.

==================================================
8. "WITHIN" / "মধ্যে" INTERPRETATION
==================================================

Expressions such as:

- সোমবারের মধ্যে
- মঙ্গলবারের মধ্যে
- সোম/মঙ্গলবারের মধ্যে
- ২০ আগস্টের মধ্যে
- তিন দিনের মধ্যে

indicate a deadline or possible completion window.

Do NOT automatically treat "এর মধ্যে" as meaning the event lasts
until that date.

For example:

"মঙ্গলবারের মধ্যে পেমেন্ট শুরু হবে"

means:

The payment-start event is expected to occur no later than Tuesday.

Therefore:

event_from = the earliest logically indicated date
event_until = Tuesday

when the wording supports such a range.

If the exact earliest date cannot be determined, event_from may be null,
but event_until MUST be resolved if it can be determined.

==================================================
9. "FROM / থেকে" INTERPRETATION
==================================================

Expressions such as:

- থেকে
- শুরু হবে
- কার্যকর হবে
- চালু হবে
- শুরু করা হবে

indicate the beginning of applicability or an event.

Example:

"বৃহস্পতিবার থেকে নতুন নিয়ম কার্যকর হবে।"

If NOTICE DATE = Wednesday 2026-08-12:

valid_from = 2026-08-13

If no ending date exists:

valid_until = null

==================================================
10. "UNTIL / পর্যন্ত" INTERPRETATION
==================================================

Expressions such as:

- পর্যন্ত
- পর্যন্ত চলবে
- পর্যন্ত কার্যকর থাকবে
- পর্যন্ত বন্ধ থাকবে
- পর্যন্ত গ্রহণ করা হবে

indicate an ending boundary.

Example:

"১০ আগস্ট থেকে ১৫ আগস্ট পর্যন্ত ক্লাস বন্ধ থাকবে."

valid_from = 2026-08-10
valid_until = 2026-08-15

==================================================
11. ONGOING INFORMATION
==================================================

Not every notice has an expiration date.

Example:

"CNPI-তে নতুন Software Lab চালু করা হয়েছে।"

This is an ongoing/current state.

Use:

temporal_type = "ONGOING"

valid_from may be the notice date if the wording indicates the
change became effective from the notice date.

valid_until = null

expiration_date = null

DO NOT mark it as expired simply because the notice is old.

==================================================
12. TIME-INDEPENDENT INFORMATION
==================================================

If the notice contains information that does not depend on a
specific date or period, use:

temporal_type = "TIME_INDEPENDENT"

Example:

"CST বিভাগে Software, Hardware, Network এবং ICT Lab রয়েছে."

Do NOT invent validity dates.

==================================================
13. EXPIRATION DATE
==================================================

Determine expiration_date ONLY when the notice explicitly or
logically indicates when the notice's instruction/information
expires.

Examples:

"এই নির্দেশনা ২০ আগস্ট পর্যন্ত কার্যকর থাকবে."

expiration_date = 2026-08-20

"এই আবেদন ১৫ আগস্ট পর্যন্ত করা যাবে."

expiration_date = 2026-08-15

If the notice describes a one-day instruction:

"১৪ আগস্ট ক্লাস বন্ধ থাকবে."

expiration_date = 2026-08-14

If no expiration can be determined:

expiration_date = null

IMPORTANT:

Do NOT use event_until as expiration_date unless the notice
clearly indicates that the notice/instruction itself expires
at that point.

==================================================
14. IMPORTANT DATE REASONING RULE
==================================================

Before returning null, ask:

"Can this date be calculated from the NOTICE DATE, NOTICE DAY,
and the wording of the notice?"

If YES:
calculate and return the exact date.

If NO:
return null.

Never return null merely because the date is expressed using
a relative word or weekday.

For example:

NOTICE DATE = 2026-08-12
NOTICE DAY = Wednesday

"আগামীকাল"
→ 2026-08-13

"বৃহস্পতিবার"
→ 2026-08-13 when the context indicates the upcoming Thursday

"সোমবার"
→ resolve to the appropriate Monday based on the notice's
temporal wording.

==================================================
15. NO CURRENT-DATE DEPENDENCY
==================================================

You MUST NOT use the actual current date.

The only calendar reference available to you is:

NOTICE DATE
+
NOTICE DAY

Your job is to determine the dates that the notice itself refers to.

The later Answer Generation system will compare these dates with
the actual current date.

==================================================
16. OUTPUT
==================================================

Return ONLY valid JSON.

Do NOT return Markdown.
Do NOT return ```json.
Do NOT add explanations.

Use EXACTLY this structure:

{
  "notice_date": "YYYY-MM-DD",
  "notice_day": "Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday",
  "temporal_type": "DATE_SPECIFIC | PERIOD | ONGOING | CONDITIONAL | TIME_SPECIFIC | TIME_INDEPENDENT | UNKNOWN",
  "valid_from": null,
  "valid_until": null,
  "events": [
    {
      "event": "",
      "condition": null,
      "event_from": null,
      "event_until": null
    }
  ],
  "expiration_date": null
}

RULE:
Use null ONLY when the value genuinely cannot be determined
from the notice.

==================================================

You will now receive the NOTICE DATE, NOTICE DAY, and NOTICE CONTENT.
Analyze the content and return ONLY the JSON structure described above.
"""

# ---------------------------------------------------------------------------
# Weekday mapping
# ---------------------------------------------------------------------------

_WEEKDAY_MAP_EN = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_temporal_context(content: str, notice_date: str | None = None) -> dict[str, Any]:
    """Perform temporal analysis on the document content.

    Parameters
    ----------
    content:
        The normalized document content (after translation and entity normalization).
    notice_date:
        Optional notice date in YYYY-MM-DD format. If not provided, uses current date.

    Returns
    -------
    dict
        Temporal analysis JSON with keys:
        - notice_date
        - notice_day
        - temporal_type
        - valid_from
        - valid_until
        - events
        - expiration_date
    """
    if not content or not content.strip():
        logger.warning("temporal_analyzer: empty content provided")
        return _get_empty_temporal_analysis()

    # Determine notice date and day
    if notice_date:
        try:
            dt = datetime.fromisoformat(notice_date)
        except (ValueError, TypeError):
            logger.warning(f"temporal_analyzer: invalid notice_date '{notice_date}', using current date")
            dt = _get_current_bst_datetime()
    else:
        dt = _get_current_bst_datetime()

    notice_date_str = dt.strftime("%Y-%m-%d")
    notice_day = _WEEKDAY_MAP_EN[dt.weekday()]

    # Build user prompt
    user_prompt = f"""NOTICE DATE:
{notice_date_str}

NOTICE DAY:
{notice_day}

NOTICE CONTENT:
{content}"""

    try:
        logger.info("temporal_analyzer: calling LLM for temporal analysis...")
        response = call_llm(_TEMPORAL_ANALYSIS_SYSTEM_PROMPT, user_prompt)
        response = response.strip()

        # Remove markdown code fences if present
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        if not response:
            logger.warning("temporal_analyzer: LLM returned empty response")
            return _get_empty_temporal_analysis(notice_date_str, notice_day)

        # Parse JSON
        temporal_data = json.loads(response)

        # Validate structure
        if not isinstance(temporal_data, dict):
            logger.error("temporal_analyzer: LLM returned non-dict JSON")
            return _get_empty_temporal_analysis(notice_date_str, notice_day)

        # Ensure required fields exist
        temporal_data.setdefault("notice_date", notice_date_str)
        temporal_data.setdefault("notice_day", notice_day)
        temporal_data.setdefault("temporal_type", "UNKNOWN")
        temporal_data.setdefault("valid_from", None)
        temporal_data.setdefault("valid_until", None)
        temporal_data.setdefault("events", [])
        temporal_data.setdefault("expiration_date", None)

        logger.info("temporal_analyzer: temporal analysis successful")
        return temporal_data

    except json.JSONDecodeError as exc:
        logger.exception("temporal_analyzer: failed to parse LLM JSON response")
        logger.error(f"temporal_analyzer: raw response was: {response[:500]}")
        return _get_empty_temporal_analysis(notice_date_str, notice_day)

    except Exception as exc:
        logger.exception("temporal_analyzer: temporal analysis failed")
        return _get_empty_temporal_analysis(notice_date_str, notice_day)


def _get_current_bst_datetime() -> datetime:
    """Get current datetime in Bangladesh Standard Time (UTC+6)."""
    utc_now = datetime.now(tz=timezone.utc)
    bst_offset = timedelta(hours=6)
    return utc_now + bst_offset


def _get_empty_temporal_analysis(notice_date: str | None = None, notice_day: str | None = None) -> dict[str, Any]:
    """Return a minimal valid temporal analysis structure."""
    if not notice_date or not notice_day:
        dt = _get_current_bst_datetime()
        notice_date = dt.strftime("%Y-%m-%d")
        notice_day = _WEEKDAY_MAP_EN[dt.weekday()]

    return {
        "notice_date": notice_date,
        "notice_day": notice_day,
        "temporal_type": "UNKNOWN",
        "valid_from": None,
        "valid_until": None,
        "events": [],
        "expiration_date": None,
    }


# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test with sample content
    sample_content = "আগামীকাল ক্লাস হবে না। পরীক্ষা ১৫ আগস্ট থেকে ২০ আগস্ট পর্যন্ত চলবে।"
    result = analyze_temporal_context(sample_content, notice_date="2026-08-14")
    print(json.dumps(result, indent=2, ensure_ascii=False))
