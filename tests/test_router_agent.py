"""
Tests for src/agents/router_agent.py
"""

from unittest.mock import patch

import pytest

from src.agents import router_agent
from src.agents.router_agent import should_retry, MAX_RETRIES
from src.workflow.state import EmailState


def _make_state(**overrides) -> EmailState:
    defaults = dict(
        user_prompt="Write a follow-up.",
        user_id="test_user",
        draft="Draft text",
        tone="formal",
        intent="follow_up",
        review_passed=False,
        retry_count=0,
    )
    defaults.update(overrides)
    return EmailState(**defaults)


# ---------------------------------------------------------------------------
# should_retry logic
# ---------------------------------------------------------------------------

def test_should_retry_false_when_review_passed():
    assert should_retry(_make_state(review_passed=True)) is False


def test_should_retry_true_when_failed_and_under_limit():
    assert should_retry(_make_state(review_passed=False, retry_count=0)) is True


def test_should_retry_false_when_retry_count_at_limit():
    assert should_retry(_make_state(review_passed=False, retry_count=MAX_RETRIES)) is False


def test_should_retry_false_when_retry_count_exceeds_limit():
    assert should_retry(_make_state(review_passed=False, retry_count=MAX_RETRIES + 1)) is False


def test_should_retry_true_just_below_limit():
    assert should_retry(_make_state(review_passed=False, retry_count=MAX_RETRIES - 1)) is True


# ---------------------------------------------------------------------------
# run() — retry path
# ---------------------------------------------------------------------------

def test_run_sets_retry_route():
    state = _make_state(review_passed=False, retry_count=0)
    with patch.object(router_agent, "log_draft"), \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile"):
        result = router_agent.run(state)

    assert result.route == "retry"
    assert result.retry_count == 1


def test_run_increments_retry_count():
    state = _make_state(review_passed=False, retry_count=1)
    with patch.object(router_agent, "log_draft"), \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile"):
        result = router_agent.run(state)

    assert result.retry_count == 2


# ---------------------------------------------------------------------------
# run() — end path
# ---------------------------------------------------------------------------

def test_run_sets_end_route_when_review_passed():
    state = _make_state(review_passed=True, draft="Final draft")
    with patch.object(router_agent, "log_draft"), \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile"):
        result = router_agent.run(state)

    assert result.route == "end"
    assert result.final_email == "Final draft"


def test_run_sets_end_route_when_retries_exhausted():
    state = _make_state(review_passed=False, retry_count=MAX_RETRIES, draft="Last draft")
    with patch.object(router_agent, "log_draft"), \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile"):
        result = router_agent.run(state)

    assert result.route == "end"
    assert result.final_email == "Last draft"


# ---------------------------------------------------------------------------
# run() — side effects on end
# ---------------------------------------------------------------------------

def test_run_calls_log_draft_on_end():
    state = _make_state(review_passed=True)
    with patch.object(router_agent, "log_draft") as mock_log, \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile"):
        router_agent.run(state)

    mock_log.assert_called_once()


def test_run_does_not_call_log_draft_on_retry():
    state = _make_state(review_passed=False, retry_count=0)
    with patch.object(router_agent, "log_draft") as mock_log, \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile"):
        router_agent.run(state)

    mock_log.assert_not_called()


def test_run_updates_profile_preferred_tone():
    state = _make_state(review_passed=True, tone="assertive", user_id="alice")
    saved_profiles = {}

    def fake_save(uid, profile):
        saved_profiles[uid] = profile

    with patch.object(router_agent, "log_draft"), \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile", side_effect=fake_save):
        router_agent.run(state)

    assert saved_profiles["alice"]["preferred_tone"] == "assertive"


def test_run_updates_drafts_summary():
    state = _make_state(review_passed=True, tone="formal", intent="meeting_request", user_id="alice")
    saved_profiles = {}

    def fake_save(uid, profile):
        saved_profiles[uid] = profile

    with patch.object(router_agent, "log_draft"), \
         patch.object(router_agent, "load_profiles", return_value={}), \
         patch.object(router_agent, "save_profile", side_effect=fake_save):
        router_agent.run(state)

    summary = saved_profiles["alice"]["drafts_summary"]
    assert "meeting_request" in summary
    assert "formal" in summary


# ---------------------------------------------------------------------------
# log_draft — real file I/O with tmp_path
# ---------------------------------------------------------------------------

def test_log_draft_writes_entry(tmp_path, monkeypatch):
    log_file = tmp_path / "drafts_log.json"
    monkeypatch.setattr(router_agent, "DRAFTS_LOG_PATH", str(log_file))

    state = EmailState(
        user_id="alice",
        intent="follow_up",
        tone="formal",
        user_prompt="Follow up.",
        draft="Dear Alice...",
        review_score=8,
    )
    router_agent.log_draft(state)

    import json
    entries = json.loads(log_file.read_text())
    assert len(entries) == 1
    assert entries[0]["user_id"] == "alice"
    assert entries[0]["intent"] == "follow_up"
    assert entries[0]["score"] == 8


def test_log_draft_caps_at_50_entries(tmp_path, monkeypatch):
    log_file = tmp_path / "drafts_log.json"
    monkeypatch.setattr(router_agent, "DRAFTS_LOG_PATH", str(log_file))

    state = EmailState(
        user_id="u", intent="x", tone="y",
        user_prompt="p", draft="d", review_score=5,
    )
    for _ in range(55):
        router_agent.log_draft(state)

    import json
    entries = json.loads(log_file.read_text())
    assert len(entries) == 50
