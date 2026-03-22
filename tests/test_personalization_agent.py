"""
Tests for src/agents/personalization_agent.py
(No LLM call — file I/O is patched via tmp_path.)
"""

import json
import os
from unittest.mock import patch

import pytest

from src.agents import personalization_agent
from src.workflow.state import EmailState


def _patch_profiles(profiles: dict):
    """Patch load_profiles to return the given dict."""
    return patch(
        "src.agents.personalization_agent.load_profiles",
        return_value=profiles,
    )


# ---------------------------------------------------------------------------
# No stored profile → all fields default to empty strings
# ---------------------------------------------------------------------------

def test_empty_profile_sets_defaults(base_state):
    with _patch_profiles({}):
        result = personalization_agent.run(base_state)

    profile = result.user_profile
    assert profile["sender_name"] == ""
    assert profile["sender_role"] == ""
    assert profile["company"] == ""
    assert profile["custom_signature"] == ""
    assert profile["previous_drafts_summary"] == ""


# ---------------------------------------------------------------------------
# Stored profile fields are merged into state
# ---------------------------------------------------------------------------

def test_stored_profile_merged(base_state):
    stored = {
        "test_user": {
            "name": "Alice",
            "role": "PM",
            "company": "Acme",
            "preferred_tone": "assertive",
            "signature": "Best, Alice",
            "drafts_summary": "Last intent: follow_up",
        }
    }
    with _patch_profiles(stored):
        result = personalization_agent.run(base_state)

    profile = result.user_profile
    assert profile["sender_name"] == "Alice"
    assert profile["sender_role"] == "PM"
    assert profile["company"] == "Acme"
    assert profile["custom_signature"] == "Best, Alice"
    assert profile["previous_drafts_summary"] == "Last intent: follow_up"


# ---------------------------------------------------------------------------
# Preferred tone applied when no explicit tone in state
# ---------------------------------------------------------------------------

def test_preferred_tone_applied_when_state_tone_missing(base_state):
    base_state.tone = None
    stored = {"test_user": {"preferred_tone": "empathetic"}}
    with _patch_profiles(stored):
        result = personalization_agent.run(base_state)

    assert result.tone == "empathetic"


def test_state_tone_not_overwritten_by_profile(base_state):
    base_state.tone = "casual"
    stored = {"test_user": {"preferred_tone": "formal"}}
    with _patch_profiles(stored):
        result = personalization_agent.run(base_state)

    assert result.tone == "casual"


# ---------------------------------------------------------------------------
# Unknown user_id → falls back to empty profile
# ---------------------------------------------------------------------------

def test_unknown_user_id_gets_empty_profile(base_state):
    base_state.user_id = "nobody"
    stored = {"test_user": {"name": "Alice"}}
    with _patch_profiles(stored):
        result = personalization_agent.run(base_state)

    assert result.user_profile["sender_name"] == ""


# ---------------------------------------------------------------------------
# save_profile / load_profiles round-trip (uses real temp file)
# ---------------------------------------------------------------------------

def test_save_and_load_profile_roundtrip(tmp_path, monkeypatch):
    profiles_file = tmp_path / "user_profiles.json"
    monkeypatch.setattr(personalization_agent, "PROFILES_PATH", str(profiles_file))

    personalization_agent.save_profile("bob", {"name": "Bob", "role": "Dev"})
    loaded = personalization_agent.load_profiles()

    assert loaded["bob"]["name"] == "Bob"
    assert loaded["bob"]["role"] == "Dev"


def test_load_profiles_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        personalization_agent,
        "PROFILES_PATH",
        str(tmp_path / "nonexistent.json"),
    )
    assert personalization_agent.load_profiles() == {}


def test_load_profiles_returns_empty_dict_on_corrupt_json(tmp_path, monkeypatch):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json")
    monkeypatch.setattr(personalization_agent, "PROFILES_PATH", str(bad_file))

    assert personalization_agent.load_profiles() == {}
