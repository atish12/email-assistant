"""
Tests for src/integrations/anthropic_client.py
"""

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.integrations.anthropic_client import call_claude, DEFAULT_MODEL


def _make_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


TARGET = "src.integrations.anthropic_client.client"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_returns_text_from_response():
    with patch(TARGET) as mock_client:
        mock_client.messages.create.return_value = _make_response("Hello!")
        result = call_claude("system", "user")

    assert result == "Hello!"


def test_uses_default_model_when_not_specified():
    with patch(TARGET) as mock_client:
        mock_client.messages.create.return_value = _make_response("ok")
        call_claude("system", "user")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == DEFAULT_MODEL


def test_passes_custom_model():
    with patch(TARGET) as mock_client:
        mock_client.messages.create.return_value = _make_response("ok")
        call_claude("system", "user", model="claude-haiku-4-5")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5"


def test_passes_temperature_and_max_tokens():
    with patch(TARGET) as mock_client:
        mock_client.messages.create.return_value = _make_response("ok")
        call_claude("system", "user", max_tokens=256, temperature=0.0)

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 256
    assert call_kwargs["temperature"] == 0.0


# ---------------------------------------------------------------------------
# Fallback on rate limit
# ---------------------------------------------------------------------------

def test_falls_back_to_fallback_model_on_429():
    with patch(TARGET) as mock_client:
        rate_limit_error = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body={},
        )
        mock_client.messages.create.side_effect = [
            rate_limit_error,
            _make_response("fallback response"),
        ]
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
    with patch(TARGET) as mock_client:
        rate_limit_error = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body={},
        )
        mock_client.messages.create.side_effect = rate_limit_error

        with pytest.raises(anthropic.RateLimitError):
            call_claude("system", "user", fallback_model=None)


def test_no_fallback_when_same_model():
    with patch(TARGET) as mock_client:
        rate_limit_error = anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body={},
        )
        mock_client.messages.create.side_effect = rate_limit_error

        with pytest.raises(anthropic.RateLimitError):
            call_claude(
                "system", "user",
                model="claude-sonnet-4-6",
                fallback_model="claude-sonnet-4-6",
            )


# ---------------------------------------------------------------------------
# Non-rate-limit errors are not caught
# ---------------------------------------------------------------------------

def test_non_rate_limit_error_propagates():
    with patch(TARGET) as mock_client:
        mock_client.messages.create.side_effect = anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(anthropic.APIConnectionError):
            call_claude("system", "user", fallback_model="claude-haiku-4-5")


# ---------------------------------------------------------------------------
# Empty content returns empty string
# ---------------------------------------------------------------------------

def test_empty_content_returns_empty_string():
    with patch(TARGET) as mock_client:
        response = MagicMock()
        response.content = []
        mock_client.messages.create.return_value = response
        result = call_claude("system", "user")

    assert result == ""
