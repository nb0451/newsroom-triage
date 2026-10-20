"""These should all pass from the start. They test the parts you did not write."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from app import engine, config


def test_routing_default_is_classify():
    branch, _ = engine.route("Arsenal beat Chelsea 2-0")
    assert branch == "classify"


def test_routing_rules_are_applied_in_order():
    branch, why = engine.route("Why did you choose that one?")
    assert branch == "explain" and "why did you" in why


def test_empty_input_is_refused_not_classified():
    tr = engine.classify("   ")
    assert tr.branch == "refuse"


def test_retrieval_returns_at_most_the_configured_number():
    hits = engine.retrieve("business earnings market shares company profit")
    assert len(hits) <= config.KNOWLEDGE_PASSAGES


def test_retrieval_respects_the_threshold():
    hits = engine.retrieve("zzzz qqqq xxxx")
    assert all(h["score"] >= config.KNOWLEDGE_THRESHOLD for h in hits)


def test_a_banned_phrase_is_blocked():
    results = engine.check("As a human I think Sports", 0.9, "classify")
    banned = [r for r in results if r["name"] == "no banned phrase"][0]
    assert banned["passed"] is False


def test_an_answer_outside_the_four_is_blocked():
    results = engine.check("Politics", 0.9, "classify")
    allowed = [r for r in results if r["name"] == "answer is one of the four"][0]
    assert allowed["passed"] is False


@pytest.mark.parametrize("raw,expected", [
    ('{"category": "Sports", "confidence": 0.9}', "Sports"),
    ('```json\n{"category":"Business","confidence":0.4}\n```', "Business"),
    ("The answer is Sci/Tech.", "Sci/Tech"),
    ("tech", "Sci/Tech"),
    ("banana", "UNPARSED"),
])
def test_model_replies_are_parsed(raw, expected):
    cat, _ = engine._parse(raw)
    assert cat == expected


def test_every_run_is_stored():
    engine.init_db()
    with engine.db() as c:
        before = c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    engine.classify("A test headline about the economy and markets")
    with engine.db() as c:
        after = c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    assert after == before + 1


def test_a_blocked_answer_never_reaches_the_user():
    original = config.CONFIDENCE_FLOOR
    config.CONFIDENCE_FLOOR = 0.99
    try:
        tr = engine.classify("Arsenal beat Chelsea 2-0")
        assert tr.blocked is True
        assert tr.final == engine.SAFE
    finally:
        config.CONFIDENCE_FLOOR = original
