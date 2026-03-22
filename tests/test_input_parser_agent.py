"""
Tests for src/agents/input_parser_agent.py
"""

import json
from unittest.mock import patch

import pytest

from src.agents import input_parser_agent
from src.workflow.state import EmailState


CLAUDE_TARGET = "src.agents.input_parser_agent.call_claude"


def _valid_response(**overrides):
    base = {
        "recipient": "Alice",
        "tone_hint": "formal",
        "intent_hint": "follow up on project",
        "constraints": ["keep it short"],
        "subject_hint": "Project Follow-Up",
        "error": None,
    }
    base.update(overrides)
    return json.dumps(base)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_sets_fields_from_valid_response(base_state):
    with patch(CLAUDE_TARGET, return_value=_valid_response()):
        result = input_parser_agent.run(base_state)

    assert result.recipient == "Alice"
    assert result.tone == "formal"
    assert result.constraints == ["keep it short"]
    assert result.subject_hint == "Project Follow-Up"
    assert result.intent_hint == "follow up on project"
    assert result.errors == []


def test_does_not_overwrite_existing_recipient(base_state):
    base_state.recipient = "Bob"
    with patch(CLAUDE_TARGET, return_value=_valid_response(recipient="Alice")):
        result = input_parser_agent.run(base_state)

    assert result.recipient == "Bob"


def test_does_not_overwrite_existing_tone(base_state):
    base_state.tone = "casual"
    with patch(CLAUDE_TARGET, return_value=_valid_response(tone_hint="formal")):
        result = input_parser_agent.run(base_state)

    assert result.tone == "casual"


# ---------------------------------------------------------------------------
# Error field in response
# ---------------------------------------------------------------------------

def test_appends_error_when_response_has_error(base_state):
    response = _valid_response(error="Prompt is too vague")
    with patch(CLAUDE_TARGET, return_value=response):
        result = input_parser_agent.run(base_state)

    assert len(result.errors) == 1
    assert "Prompt is too vague" in result.errors[0]


# ---------------------------------------------------------------------------
# JSON parse failure fallback
# ---------------------------------------------------------------------------

def test_fallback_on_invalid_json(base_state):
    with patch(CLAUDE_TARGET, return_value="not valid json {{"):
        result = input_parser_agent.run(base_state)

    assert result.intent_hint == base_state.user_prompt
    assert result.constraints == []
    assert result.errors == []


# ---------------------------------------------------------------------------
# Recipient context forwarded to Claude
# ---------------------------------------------------------------------------

def test_recipient_context_included_in_call(base_state):
    base_state.recipient = "Sarah"
    with patch(CLAUDE_TARGET, return_value=_valid_response()) as mock_call:
        input_parser_agent.run(base_state)

    user_input_arg = mock_call.call_args[0][1]
    assert "Sarah" in user_input_arg


# ---------------------------------------------------------------------------
# Null fields in response
# ---------------------------------------------------------------------------

def test_handles_null_subject_and_recipient(base_state):
    response = _valid_response(recipient=None, subject_hint=None)
    with patch(CLAUDE_TARGET, return_value=response):
        result = input_parser_agent.run(base_state)

    assert result.subject_hint is None
    assert result.recipient is None
