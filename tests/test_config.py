"""
Three of these fail on purpose when you start.

They are not broken. They describe the three things your assistant is
missing, and they turn green when you fix config.py. Run them with:

    pytest -q

Everything in tests/test_machinery.py should pass from the beginning.
If one of those fails, something is actually wrong. Tell your instructor.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import config

CATS = ["World", "Sports", "Business", "Sci/Tech"]


def test_prompt_names_all_four_categories():
    """[FAILS UNTIL YOU FIX IT] The prompt must name all four categories."""
    p = config.SYSTEM_PROMPT
    missing = [c for c in CATS if c.lower() not in p.lower()]
    assert not missing, f"your prompt never mentions: {missing}"


def test_prompt_says_what_to_do_when_two_fit():
    """[FAILS UNTIL YOU FIX IT] The prompt must give a tie-break rule."""
    p = config.SYSTEM_PROMPT.lower()
    signals = ["if two", "both fit", "tie", "mostly about", "choose the one",
               "more than one", "closest"]
    found = [s for s in signals if s in p]
    assert found, (
        "your prompt does not say what to do when an item fits two categories. "
        "Without that rule the model picks differently every time."
    )


def test_a_confidence_floor_has_been_chosen():
    """[FAILS UNTIL YOU FIX IT] You must decide when the app should not guess."""
    assert config.CONFIDENCE_FLOOR > 0, (
        "CONFIDENCE_FLOOR is still 0.00, which means the app will never admit "
        "it does not know. Pick a number you can defend."
    )
