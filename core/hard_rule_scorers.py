"""Deterministic Tavus hard-rule scorers over persona transcripts.

Each rule scores a list of assistant turns and returns the fraction of turns
that comply (0.0-1.0), or None when there are no turns to score. These mirror
the spoken-output hard rules from the persona engineering manual: they are
cheap, deterministic checks meant to run on every benchmark row and, later,
as Braintrust code scorers on live logs.
"""
import re

_EM_DASH = "—"

_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),  # emoji blocks incl. emoticons, symbols, extended
    (0x2600, 0x27BF),    # misc symbols + dingbats
    (0x2B00, 0x2BFF),    # arrows/stars (e.g. 2B50)
    (0xFE00, 0xFE0F),    # variation selectors
)

_URL_RE = re.compile(
    r"(https?://|www\.|\b[a-z0-9-]+\.(?:com|io|org|net|ai|dev|co)\b)", re.IGNORECASE
)

_MARKDOWN_RE = re.compile(r"(\*|`|^#{1,6}\s|^\s*-\s)", re.MULTILINE)

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")


def _fraction(turns, is_compliant):
    if not turns:
        return None
    compliant = sum(1 for t in turns if is_compliant(t))
    return compliant / len(turns)


def rule_lowercase(turns):
    """No caps anywhere in spoken output."""
    return _fraction(turns, lambda t: not any(c.isupper() for c in t))


def rule_no_em_dash(turns):
    return _fraction(turns, lambda t: _EM_DASH not in t)


def rule_no_emoji(turns):
    def clean(t):
        return not any(lo <= ord(c) <= hi for c in t for lo, hi in _EMOJI_RANGES)

    return _fraction(turns, clean)


def rule_numbers_spelled(turns):
    """Digits must not appear; numbers are spelled out in speech."""
    return _fraction(turns, lambda t: not any(c.isdigit() for c in t))


def rule_no_markdown(turns):
    return _fraction(turns, lambda t: not _MARKDOWN_RE.search(t))


def rule_no_urls(turns):
    return _fraction(turns, lambda t: not _URL_RE.search(t))


def rule_brevity(turns):
    """One to three sentences per turn."""

    def ok(t):
        sentences = [s for s in _SENTENCE_SPLIT_RE.split(t) if s.strip()]
        return 1 <= len(sentences) <= 3

    return _fraction(turns, ok)


def rule_one_question(turns):
    return _fraction(turns, lambda t: t.count("?") <= 1)


ALL_RULES = {
    "rule_lowercase": rule_lowercase,
    "rule_no_em_dash": rule_no_em_dash,
    "rule_no_emoji": rule_no_emoji,
    "rule_numbers_spelled": rule_numbers_spelled,
    "rule_no_markdown": rule_no_markdown,
    "rule_no_urls": rule_no_urls,
    "rule_brevity": rule_brevity,
    "rule_one_question": rule_one_question,
}


def score_assistant_turns(turns):
    """Run every hard rule; returns {rule_name: fraction} ({} when no turns)."""
    if not turns:
        return {}
    return {name: fn(turns) for name, fn in ALL_RULES.items()}
