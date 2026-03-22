"""
Tests for src/agents/intent_detection_agent.py
"""

import json
from unittest.mock import patch

import pytest

from src.agents import intent_detection_agent
from src.agents.intent_detection_agent import INTENTS
from src.workflow.state import EmailState


CLAUDE_TARGET = "src.agents.intent_detection_agent.call_claude"


def _response(intent="follow_up", confidence=0.9):
    return json.dumps({
        "intent": intent,
        "confidence": confidence,
        "reasoning": "The user wants to follow up.",
    })


# ---------------------------------------------------------------------------
# Happy path — every valid intent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("intent", INTENTS)
def test_sets_each_valid_intent(base_state, intent):
    with patch(CLAUDE_TARGET, return_value=_response(intent=intent)):
        result = intent_detection_agent.run(base_state)

    assert result.intent == intent


# ---------------------------------------------------------------------------
# Unknown intent normalised to "other"
# ---------------------------------------------------------------------------

def test_unknown_intent_falls_back_to_other(base_state):
    with patch(CLAUDE_TARGET, return_value=_response(intent="negotiate_salary")):
        result = intent_detection_agent.run(base_state)

    assert result.intent == "other"


# ---------------------------------------------------------------------------
# Invalid JSON fallback
# ---------------------------------------------------------------------------

def test_invalid_json_falls_back_to_other(base_state):
    with patch(CLAUDE_TARGET, return_value="[[not json]]"):
        result = intent_detection_agent.run(base_state)

    assert result.intent == "other"


# ---------------------------------------------------------------------------
# Claude receives the right context
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Skip detection when intent already set by user
# ---------------------------------------------------------------------------

def test_skips_detection_when_intent_already_set(base_state):
    base_state.intent = "follow_up"
    with patch(CLAUDE_TARGET) as mock_call:
        result = intent_detection_agent.run(base_state)

    mock_call.assert_not_called()
    assert result.intent == "follow_up"


def test_runs_detection_when_intent_is_none(base_state):
    base_state.intent = None
    with patch(CLAUDE_TARGET, return_value=_response(intent="outreach")) as mock_call:
        result = intent_detection_agent.run(base_state)

    mock_call.assert_called_once()
    assert result.intent == "outreach"


def test_runs_detection_when_intent_not_in_valid_list(base_state):
    base_state.intent = "invalid_intent"
    with patch(CLAUDE_TARGET, return_value=_response(intent="outreach")) as mock_call:
        result = intent_detection_agent.run(base_state)

    mock_call.assert_called_once()


def test_user_message_contains_prompt_and_recipient(base_state):
    base_state.recipient = "Manager"
    base_state.intent_hint = "schedule a meeting"
    with patch(CLAUDE_TARGET, return_value=_response()) as mock_call:
        intent_detection_agent.run(base_state)

    user_msg = mock_call.call_args[0][1]
    assert base_state.user_prompt in user_msg
    assert "Manager" in user_msg
    assert "schedule a meeting" in user_msg
