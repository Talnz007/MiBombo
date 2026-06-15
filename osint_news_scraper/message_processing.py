"""
message_processing.py — Robust OSINT message pre-processing
============================================================
Task 1: Strip [CATEGORY: N] tags from Grok output (improved version).
Task 2: Extract [PRIORITY: N] tags for dynamic routing to dispatch_message().

Integrates with the existing pipeline:
  - ai_reporter.py   (parse_category already lives there — this upgrades it)
  - whatsapp_dispatcher.py (clean_osint_report is applied before send)
  - main.py           (calls parse_category then dispatches)

Author: automated
"""

import re
from dataclasses import dataclass
from typing import Optional


# ════════════════════════════════════════════════════════════════════════════════
# TASK 1 — Robust Category Stripping
# ════════════════════════════════════════════════════════════════════════════════
#
# Handles every observed Grok formatting quirk:
#   ✔ Standard:          [CATEGORY: 1]
#   ✔ No space:          [CATEGORY:1]
#   ✔ Extra spaces:      [ CATEGORY :  2 ]
#   ✔ Mixed case:        [Category: 2], [category:1]
#   ✔ Curly/smart quotes or brackets Grok sometimes emits
#   ✔ Bare label:        Category 1  /  CATEGORY 2  (no brackets)
#   ✔ Trailing newlines left behind after removal

# --- Primary pattern: bracketed tag  [CATEGORY: N] ---
_CATEGORY_BRACKETED_RE = re.compile(
    r'\[?\s*'          # optional opening bracket + whitespace
    r'CATEGORY'        # literal keyword
    r'\s*[:：]\s*'     # colon (ASCII or fullwidth) with optional spaces
    r'([1-3])'         # the category digit we care about
    r'\s*\]?'          # optional closing bracket + whitespace
    ,
    re.IGNORECASE,
)

# --- Fallback pattern: bare text   "Category 1" / "CATEGORY 2" ---
_CATEGORY_BARE_RE = re.compile(
    r'(?:^|\n)\s*'     # start of string or newline (tag is usually on its own line)
    r'CATEGORY'
    r'\s+'
    r'([1-3])'
    r'\s*(?:\n|$)'     # followed by newline or end-of-string
    ,
    re.IGNORECASE,
)


def strip_category(text: str, default: int = 1) -> tuple[int, str]:
    """
    Extract and remove the category tag from Grok's response.

    Returns
    -------
    (category_int, cleaned_text)
        category_int : 1 (global) | 2 (regional) | 3 (other)
        cleaned_text : the message with the tag removed and no orphan blank lines

    Falls back to `default` (1 = global) if no valid tag is found.
    """
    category = default

    # Try the bracketed form first (most common)
    match = _CATEGORY_BRACKETED_RE.search(text)
    if match:
        category = int(match.group(1))
        text = _CATEGORY_BRACKETED_RE.sub('', text, count=1)
    else:
        # Try the bare form
        match = _CATEGORY_BARE_RE.search(text)
        if match:
            category = int(match.group(1))
            text = _CATEGORY_BARE_RE.sub('\n', text, count=1)

    # Clean up orphan blank lines left behind by removal
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    if match:
        print(f"[+] strip_category: extracted CATEGORY {category}")
    else:
        print(f"[!] strip_category: no tag found, defaulting to {default}")

    return category, text


# ════════════════════════════════════════════════════════════════════════════════
# TASK 2 — Priority Extraction & Routing
# ════════════════════════════════════════════════════════════════════════════════
#
# Expected Grok output:  [PRIORITY: 1]  /  [PRIORITY: 2]  /  [PRIORITY: 3]
#
# Handles same edge cases as category:
#   ✔ [PRIORITY: 1], [priority:3], [ PRIORITY : 2 ]
#   ✔ Fullwidth colon ：
#   ✔ Missing brackets
#   ✔ Fallback to Priority 2 if tag absent or malformed

_PRIORITY_BRACKETED_RE = re.compile(
    r'\[?\s*'
    r'PRIORITY'
    r'\s*[:：]\s*'
    r'([1-3])'
    r'\s*\]?'
    ,
    re.IGNORECASE,
)

# Catches malformed tags like [PRIORITY: 99] or [PRIORITY: abc] so they
# never leak into the WhatsApp payload, even though they don't set a valid priority.
_PRIORITY_MALFORMED_RE = re.compile(
    r'\[\s*PRIORITY\s*[:：]\s*\S+\s*\]',
    re.IGNORECASE,
)

_PRIORITY_BARE_RE = re.compile(
    r'(?:^|\n)\s*'
    r'PRIORITY'
    r'\s+'
    r'([1-3])'
    r'\s*(?:\n|$)'
    ,
    re.IGNORECASE,
)

DEFAULT_PRIORITY = 2   # Safe middle-ground if Grok omits the tag


@dataclass
class ProcessedMessage:
    """Result of processing a raw Grok response for priority dispatch."""
    payload: str               # Clean text ready for WhatsApp (no tags, no orphan whitespace)
    priority: int              # 1 = critical, 2 = important, 3 = routine
    tag_was_present: bool      # False ⇒ we fell back to DEFAULT_PRIORITY


def extract_priority(raw_text: str) -> ProcessedMessage:
    """
    Parse and strip the [PRIORITY: N] tag from Grok's raw output.

    Returns a ProcessedMessage with:
      • .payload   — clean string, safe for WhatsApp dispatch
      • .priority  — extracted int (1-3), or DEFAULT_PRIORITY on fallback
      • .tag_was_present — whether a valid tag was actually found

    Usage
    -----
        result = extract_priority(grok_output)
        dispatch_message(result.payload, result.priority)
    """
    priority = DEFAULT_PRIORITY
    tag_found = False

    # Try bracketed form first
    match = _PRIORITY_BRACKETED_RE.search(raw_text)
    if match:
        priority = int(match.group(1))
        tag_found = True
        raw_text = _PRIORITY_BRACKETED_RE.sub('', raw_text, count=1)
    else:
        # Try bare form
        match = _PRIORITY_BARE_RE.search(raw_text)
        if match:
            priority = int(match.group(1))
            tag_found = True
            raw_text = _PRIORITY_BARE_RE.sub('\n', raw_text, count=1)

    # Strip any remaining malformed priority tags that didn't match [1-3]
    raw_text = _PRIORITY_MALFORMED_RE.sub('', raw_text)

    # Scrub orphan blank lines and leading/trailing whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', raw_text)
    cleaned = cleaned.strip()

    if tag_found:
        print(f"[+] extract_priority: found PRIORITY {priority}")
    else:
        print(f"[!] extract_priority: no tag found → defaulting to {DEFAULT_PRIORITY}")

    return ProcessedMessage(
        payload=cleaned,
        priority=priority,
        tag_was_present=tag_found,
    )


# ════════════════════════════════════════════════════════════════════════════════
# Combined helper — strip BOTH tags in one call
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class FullyProcessedMessage:
    """Result of stripping both category and priority from Grok output."""
    payload: str
    category: int       # 1 = global, 2 = regional, 3 = other
    priority: int       # 1 = critical, 2 = important, 3 = routine
    category_found: bool
    priority_found: bool


def process_grok_output(
    raw_text: str,
    default_category: int = 1,
    default_priority: int = 2,
) -> FullyProcessedMessage:
    """
    One-shot extraction of both [CATEGORY: N] and [PRIORITY: N] tags.

    Use this if you adopt priority routing alongside the existing category system.
    """
    cat, text = strip_category(raw_text, default=default_category)
    result = extract_priority(text)

    return FullyProcessedMessage(
        payload=result.payload,
        category=cat,
        priority=result.priority if result.tag_was_present else default_priority,
        category_found=(cat != default_category or _CATEGORY_BRACKETED_RE.search(raw_text) is not None),
        priority_found=result.tag_was_present,
    )


# ════════════════════════════════════════════════════════════════════════════════
# Self-test
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # ── Task 1 tests ──
    _cat_tests = [
        ("[CATEGORY: 1]\n*Aoa, sir*\n🔶 Subject...",                     1),
        ("[CATEGORY:2]\n*Aoa, sir*",                                      2),
        ("[ category : 3 ]\n*Aoa, sir*",                                  3),
        ("  [Category:  1]  \n\n*Aoa, sir*",                              1),
        ("Category 2\n*Aoa, sir*",                                        2),
        ("*Aoa, sir*\n🔶 Subject...",                                     1),  # missing → default 1
        ("[CATEGORY：2]\n*Aoa, sir*",                                     2),  # fullwidth colon
    ]
    print("═" * 60)
    print("TASK 1 — Category Stripping")
    print("═" * 60)
    all_pass = True
    for i, (inp, expected_cat) in enumerate(_cat_tests):
        cat, cleaned = strip_category(inp)
        ok = cat == expected_cat and "[CATEGORY" not in cleaned.upper() and "CATEGORY " not in cleaned.upper()
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"  {status} Test {i+1}: expected cat={expected_cat}, got cat={cat}")
        if not ok:
            print(f"       cleaned: {repr(cleaned)}")

    # ── Task 2 tests ──
    _pri_tests = [
        ("[PRIORITY: 1]\n*Aoa, sir*\n🔶 Breaking...",                    1, True),
        ("[PRIORITY:3]\n*Aoa, sir*",                                      3, True),
        ("[ priority : 2 ]\n*Aoa, sir*",                                  2, True),
        ("  [Priority:  1]  \n\n*Aoa, sir*",                              1, True),
        ("PRIORITY 3\n*Aoa, sir*",                                        3, True),
        ("*Aoa, sir*\n🔶 No tag at all...",                               2, False),  # default
        ("[PRIORITY：1]\n*Aoa, sir*",                                     1, True),   # fullwidth colon
        ("[PRIORITY: 99]\n*Aoa, sir*",                                    2, False),  # invalid digit → stripped but defaults to 2
    ]
    print(f"\n{'═' * 60}")
    print("TASK 2 — Priority Extraction")
    print("═" * 60)
    for i, (inp, expected_pri, expected_found) in enumerate(_pri_tests):
        result = extract_priority(inp)
        ok = (
            result.priority == expected_pri
            and result.tag_was_present == expected_found
            and "PRIORITY" not in result.payload.upper()
        )
        status = "✅" if ok else "❌"
        if not ok:
            all_pass = False
        print(f"  {status} Test {i+1}: expected pri={expected_pri} found={expected_found}, "
              f"got pri={result.priority} found={result.tag_was_present}")
        if not ok:
            print(f"       payload: {repr(result.payload)}")

    # ── Combined test ──
    combined_input = "[CATEGORY: 2]\n[PRIORITY: 1]\n*Aoa, sir*\n🔶 Subject : *Breaking Alert*\n *Regards*"
    full = process_grok_output(combined_input)
    ok = full.category == 2 and full.priority == 1 and "CATEGORY" not in full.payload.upper() and "PRIORITY" not in full.payload.upper()
    status = "✅" if ok else "❌"
    if not ok:
        all_pass = False
    print(f"\n  {status} Combined test: cat={full.category} pri={full.priority}")
    print(f"       payload: {repr(full.payload[:80])}")

    print(f"\n{'═' * 60}")
    print("🎉 ALL TESTS PASSED" if all_pass else "❌ SOME TESTS FAILED")
    print(f"{'═' * 60}")
