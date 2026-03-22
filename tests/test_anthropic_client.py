"""
Tests for src/integrations/anthropic_client.py
"""

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.integrations.anthropic_client import call_claude, DEFAULT_MODEL

# Patch anthropic.Anthropic constructor so no real client is created
TARGET = "src.integrations.anthropic_client.anthropic.Anthropic"


def _make_client(text: str):
    """Return a mock Anthropic client whose messages.create returns a text block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = response
    return mock_client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_returns_text_from_response():
    with patch(TARGET, return_value=_make_client("Hello!")):
        result = call_claude("system", "user")
    assert result == "Hello!"


def test_uses_default_model_when_not_specified():
    mock_client = _make_client("ok")
    with patch(TARGET, return_value=mock_client):
        call_claude("system", "user")
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == DEFAULT_MODEL


def test_passes_custom_model():
    mock_client = _make_client("ok")
    with patch(TARGET, return_value=mock_client):
        call_claude("system", "user", model="claude-haiku-4-5")
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5"


def test_passes_temperature_and_max_tokens():
    mock_client = _make_client("ok")
    with patch(TARGET, return_value=mock_client):
        call_claude("system", "user", max_tokens=256, temperature=0.0)
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 256
    assert call_kwargs["temperature"] == 0.0


# ---------------------------------------------------------------------------
# Fallback on rate limit
# ---------------------------------------------------------------------------

def test_falls_back_to_fallback_model_on_429():
    rate_limit_error = anthropic.RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body={},
    )
    block = MagicMock()
    block.type = "text"
    block.text = "fallback response"
    fallback_response = MagicMock()
    fallback_response.content = [block]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [rate_limit_error, fallback_response]

    with patch(TARGET, return_value=mock_client):
        result = call_claude(
            "system", "user",
            model="claude-sonnet-4-6",
            fallback_model="claude-haiku-4-5",
        )

    assert result == "fallback response"
    assert mock_client.messages.create.call_count == 2
    second_call_model = mock_client.messages.create.call_args_list[1][1]["model"]
    assert second_call_model == "claude-haiku-4-5"


def test_no_fallback_when_fallback_model_is_none():
    rate_limit_error = anthropic.RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body={},
    )
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = rate_limit_error

    with patch(TARGET, return_value=mock_client):
        with pytest.raises(anthropic.RateLimitError):
            call_claude("system", "user", fallback_model=None)


def test_no_fallback_when_same_model():
    rate_limit_error = anthropic.RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429),
        body={},
    )
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = rate_limit_error

    with patch(TARGET, return_value=mock_client):
        with pytest.raises(anthropic.RateLimitError):
            call_claude(
                "system", "user",
                model="claude-sonnet-4-6",
                fallback_model="claude-sonnet-4-6",
            )


# ---------------------------------------------------------------------------
# Non-rate-limit errors propagate
# ---------------------------------------------------------------------------

def test_non_rate_limit_error_propagates():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APIConnectionError(
        request=MagicMock()
    )
    with patch(TARGET, return_value=mock_client):
        with pytest.raises(anthropic.APIConnectionError):
            call_claude("system", "user", fallback_model="claude-haiku-4-5")


# ---------------------------------------------------------------------------
# Empty content returns empty string
# ---------------------------------------------------------------------------

def test_empty_content_returns_empty_string():
    mock_client = MagicMock()
    response = MagicMock()
    response.content = []
    mock_client.messages.create.return_value = response

    with patch(TARGET, return_value=mock_client):
        result = call_claude("system", "user")

    assert result == ""
