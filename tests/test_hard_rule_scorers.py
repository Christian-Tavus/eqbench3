"""Tests for the deterministic Tavus hard-rule transcript scorers."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.hard_rule_scorers import (
    rule_lowercase,
    rule_no_em_dash,
    rule_no_emoji,
    rule_numbers_spelled,
    rule_no_markdown,
    rule_no_urls,
    rule_brevity,
    rule_one_question,
    score_assistant_turns,
)


def test_lowercase_compliant():
    assert rule_lowercase(["hey there, how are you doing today?"]) == 1.0


def test_lowercase_violation():
    assert rule_lowercase(["I think that's GREAT news!"]) == 0.0


def test_lowercase_fraction_across_turns():
    assert rule_lowercase(["all good here.", "But THIS one shouts."]) == 0.5


def test_no_em_dash():
    assert rule_no_em_dash(["a normal turn, with commas."]) == 1.0
    assert rule_no_em_dash(["a turn — with an em-dash."]) == 0.0


def test_no_emoji():
    assert rule_no_emoji(["plain text only"]) == 1.0
    assert rule_no_emoji(["sounds great \U0001F600"]) == 0.0
    assert rule_no_emoji(["star ⭐ struck"]) == 0.0


def test_numbers_spelled():
    assert rule_numbers_spelled(["that costs fifty-nine dollars a month."]) == 1.0
    assert rule_numbers_spelled(["that costs 59 dollars a month."]) == 0.0


def test_no_markdown():
    assert rule_no_markdown(["just plain spoken words here."]) == 1.0
    assert rule_no_markdown(["this is **bold** claim"]) == 0.0
    assert rule_no_markdown(["- first bullet\n- second bullet"]) == 0.0
    assert rule_no_markdown(["# heading style"]) == 0.0
    assert rule_no_markdown(["some `code` here"]) == 0.0


def test_no_urls():
    assert rule_no_urls(["check the pricing page for details."]) == 1.0
    assert rule_no_urls(["go to https://tavus.io for details."]) == 0.0
    assert rule_no_urls(["go to www.tavus.io for details."]) == 0.0
    assert rule_no_urls(["go to tavus.io for details."]) == 0.0


def test_brevity_one_to_three_sentences():
    assert rule_brevity(["short and sweet."]) == 1.0
    assert rule_brevity(["one. two. three."]) == 1.0
    assert rule_brevity(["one. two. three. four."]) == 0.0


def test_one_question_per_turn():
    assert rule_one_question(["how are you today?"]) == 1.0
    assert rule_one_question(["how are you? and what's your name?"]) == 0.0
    assert rule_one_question(["no questions at all."]) == 1.0


def test_empty_turns_returns_none():
    assert rule_lowercase([]) is None
    assert score_assistant_turns([]) == {}


def test_score_assistant_turns_shape():
    scores = score_assistant_turns(["hey, how are you?"])
    expected_keys = {
        "rule_lowercase",
        "rule_no_em_dash",
        "rule_no_emoji",
        "rule_numbers_spelled",
        "rule_no_markdown",
        "rule_no_urls",
        "rule_brevity",
        "rule_one_question",
    }
    assert set(scores.keys()) == expected_keys
    assert all(0.0 <= v <= 1.0 for v in scores.values())
