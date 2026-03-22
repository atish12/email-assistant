"""
Tests for src/agents/review_agent.py
"""

import json
from unittest.mock import patch

import pytest

from src.agents import review_agent
from src.workflow.state import EmailState


CLAUDE_TARGET = "src.agents.review_agent.call_claude"


def _response(**overrides):
    base = {
        "passed": True,
        "score": 8,
        "tone_aligned": True,
        "grammar_ok": True,
        "intent_fulfilled": True,
        "feedback": "",
        "improved_subject": None,
    }
    base.update(overrides)
    return json.dumps(base)


def _make_state(**overrides) -> EmailState:
    defaults = dict(
        user_prompt="Write a follow-up email.",
        intent="follow_up",
        tone="formal",
        constraints=[],
        draft="Subject: Follow-Up\n\nDear Alice,\n\nChecking in.\n\nBest,\nBob",
    )
    defaults.update(overrides)
    return EmailState(**defaults)


# ---------------------------------------------------------------------------
# Passing review
# ---------------------------------------------------------------------------

def test_passing_review_sets_fields():
    state = _make_state()
    with patch(CLAUDE_TARGET, return_value=_response(passed=True, score=9)):
        result = review_agent.run(state)

    assert result.review_passed is True
    assert result.review_score == 9
    assert result.review_feedback == ""


# ---------------------------------------------------------------------------
# Failing review
# ---------------------------------------------------------------------------

def test_failing_review_sets_feedback():
    feedback = "The tone is too casual for a formal email."
    state = _make_state()
    with patch(CLAUDE_TARGET, return_value=_response(passed=False, score=4, feedback=feedback)):
        result = review_agent.run(state)

    assert result.review_passed is False
    assert result.review_score == 4
    assert result.review_feedback == feedback


# ---------------------------------------------------------------------------
# Improved subject propagated
# ---------------------------------------------------------------------------

def test_improved_subject_updates_state():
    state = _make_state()
    with patch(CLAUDE_TARGET, return_value=_response(improved_subject="Re: Project Update")):
        result = review_agent.run(state)

    assert result.subject_hint == "Re: Project Update"


def test_null_improved_subject_does_not_set_subject_hint():
    state = _make_state()
    with patch(CLAUDE_TARGET, return_value=_response(improved_subject=None)):
        result = review_agent.run(state)

    assert result.subject_hint is None


# ---------------------------------------------------------------------------
# Invalid JSON fallback → fail-safe defaults
# ---------------------------------------------------------------------------

def test_invalid_json_fallback():
    state = _make_state()
    with patch(CLAUDE_TARGET, return_value="not json"):
        result = review_agent.run(state)

    assert result.review_passed is True
    assert result.review_score == 7
    assert result.review_feedback == ""


# ---------------------------------------------------------------------------
# Constraints included in Claude user message
# ---------------------------------------------------------------------------

def test_constraints_in_user_message():
    state = _make_state(constraints=["keep it short", "no jargon"])
    with patch(CLAUDE_TARGET, return_value=_response()) as mock_call:
        review_agent.run(state)

    user_msg = mock_call.call_args[0][1]
    assert "keep it short" in user_msg
    assert "no jargon" in user_msg
