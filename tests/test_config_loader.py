"""
Tests for src/integrations/config_loader.py
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from src.integrations import config_loader


def _write_yaml(path: str, data: dict) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(data, f)


# ---------------------------------------------------------------------------
# Helpers — clear lru_cache between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    config_loader._load.cache_clear()
    yield
    config_loader._load.cache_clear()


# ---------------------------------------------------------------------------
# Missing config file — falls back to defaults
# ---------------------------------------------------------------------------

def test_missing_file_returns_defaults():
    with patch.object(config_loader, "_CONFIG_PATH", "/nonexistent/mcp.yaml"):
        cfg = config_loader.get_agent_config("draft_writer")

    assert cfg["model"] == config_loader._DEFAULTS["model"]
    assert cfg["max_tokens"] == config_loader._DEFAULTS["max_tokens"]
    assert "fallback_model" in cfg


# ---------------------------------------------------------------------------
# Per-agent model loaded correctly
# ---------------------------------------------------------------------------

def test_agent_model_overrides_primary():
    data = {
        "model": {"primary": "claude-sonnet-4-6", "fallback": "claude-haiku-4-5"},
        "agents": {
            "input_parser": {"model": "claude-haiku-4-5", "max_tokens": 512, "temperature": 0.0}
        },
    }
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.safe_dump(data, f)
        tmp_path = f.name

    try:
        with patch.object(config_loader, "_CONFIG_PATH", tmp_path):
            cfg = config_loader.get_agent_config("input_parser")
        assert cfg["model"] == "claude-haiku-4-5"
        assert cfg["max_tokens"] == 512
        assert cfg["temperature"] == 0.0
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Agent without explicit model uses primary
# ---------------------------------------------------------------------------

def test_agent_without_model_uses_primary():
    data = {
        "model": {"primary": "claude-sonnet-4-6", "fallback": "claude-haiku-4-5"},
        "agents": {},
    }
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.safe_dump(data, f)
        tmp_path = f.name

    try:
        with patch.object(config_loader, "_CONFIG_PATH", tmp_path):
            cfg = config_loader.get_agent_config("draft_writer")
        assert cfg["model"] == "claude-sonnet-4-6"
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Fallback model is passed through
# ---------------------------------------------------------------------------

def test_fallback_model_in_config():
    data = {
        "model": {"primary": "claude-sonnet-4-6", "fallback": "claude-haiku-4-5"},
        "agents": {},
    }
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.safe_dump(data, f)
        tmp_path = f.name

    try:
        with patch.object(config_loader, "_CONFIG_PATH", tmp_path):
            cfg = config_loader.get_agent_config("review")
        assert cfg["fallback_model"] == "claude-haiku-4-5"
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Real mcp.yaml loads without error
# ---------------------------------------------------------------------------

def test_real_config_loads():
    cfg = config_loader.get_agent_config("draft_writer")
    assert "model" in cfg
    assert "max_tokens" in cfg
    assert "temperature" in cfg
    assert "fallback_model" in cfg
