"""
Tests for src/agents/draft_writer_agent.py
"""

from unittest.mock import patch

import pytest

from src.agents import draft_writer_agent
from src.agents.draft_writer_agent import build_system_prompt
from src.workflow.state import EmailState


CLAUDE_TARGET = "src.agents.draft_writer_agent.call_claude"

FAKE_DRAFT = "Subject: Follow-Up\n\nDear Alice,\n\nJust checking in.\n\nBest regards,\nBob"


def _make_state(**overrides) -> EmailState:
    defaults = dict(
        user_prompt="Write a follow-up email to Alice.",
        recipient="Alice",
        intent="follow_up",
        tone="formal",
        tone_guide={
            "description": "Professional, respectful",
            "vocabulary": "No contractions",
            "greeting": "Dear [Name],",
            "closing": "Best regards,",
            "avoid": "slang",
        },
        user_profile={
            "sender_name": "Bob",
            "sender_role": "Engineer",
            "company": "Acme",
            "custom_signature": "Bob\nEngineer, Acme",
            "previous_drafts_summary": "",
        },
        constraints=[],
        subject_hint="Project Follow-Up",
        retry_count=0,
        review_feedback=None,
    )
    defaults.update(overrides)
    return EmailState(**defaults)


# ---------------------------------------------------------------------------
# run() sets draft from Claude response
# ---------------------------------------------------------------------------

def test_run_sets_draft():
    state = _make_state()
    with patch(CLAUDE_TARGET, return_value=FAKE_DRAFT):
        result = draft_writer_agent.run(state)

    assert result.draft == FAKE_DRAFT


# ---------------------------------------------------------------------------
# build_system_prompt content checks
# ---------------------------------------------------------------------------

def test_system_prompt_includes_intent():
    state = _make_state(intent="meeting_request")
    prompt = build_system_prompt(state)
    assert "meeting_request" in prompt


def test_system_prompt_includes_tone():
    state = _make_state(tone="casual")
    prompt = build_system_prompt(state)
    assert "casual" in prompt


def test_system_prompt_includes_profile_fields():
    state = _make_state()
    prompt = build_system_prompt(state)
    assert "Bob" in prompt
    assert "Engineer" in prompt
    assert "Acme" in prompt
    assert "Bob\nEngineer, Acme" in prompt


def test_system_prompt_includes_constraints():
    state = _make_state(constraints=["keep it under 100 words", "include meeting link"])
    prompt = build_system_prompt(state)
    assert "keep it under 100 words" in prompt
    assert "include meeting link" in prompt


def test_system_prompt_omits_constraint_section_when_empty():
    state = _make_state(constraints=[])
    prompt = build_system_prompt(state)
    assert "Constraints to follow" not in prompt


def test_system_prompt_includes_retry_feedback():
    state = _make_state(retry_count=1, review_feedback="Tone is too casual.")
    prompt = build_system_prompt(state)
    assert "Tone is too casual." in prompt
    assert "Previous draft had issues" in prompt


def test_system_prompt_omits_retry_note_on_first_attempt():
    state = _make_state(retry_count=0, review_feedback=None)
    prompt = build_system_prompt(state)
    assert "Previous draft had issues" not in prompt


def test_system_prompt_omits_profile_section_when_empty():
    state = _make_state(user_profile={
        "sender_name": "",
        "sender_role": "",
        "company": "",
        "custom_signature": "",
        "previous_drafts_summary": "",
    })
    prompt = build_system_prompt(state)
    assert "Sender name" not in prompt
    assert "Sender role" not in prompt
