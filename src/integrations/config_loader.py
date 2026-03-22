"""
MCP Config Loader
-----------------
Reads config/mcp.yaml and provides per-agent model settings.
Falls back to sensible defaults if the file is missing or a key is absent.
"""

import os
from functools import lru_cache
from typing import Any

import yaml

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "mcp.yaml"
)

_DEFAULTS = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 1024,
    "temperature": 0.7,
}


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    path = os.path.abspath(_CONFIG_PATH)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def get_agent_config(agent_name: str) -> dict[str, Any]:
    """Return resolved model config for a given agent name."""
    cfg = _load()
    primary_model = cfg.get("model", {}).get("primary", _DEFAULTS["model"])
    fallback_model = cfg.get("model", {}).get("fallback", _DEFAULTS["model"])
    agent_cfg = cfg.get("agents", {}).get(agent_name, {})

    model = agent_cfg.get("model") or primary_model
    return {
        "model": model,
        "fallback_model": fallback_model,
        "max_tokens": agent_cfg.get("max_tokens") or _DEFAULTS["max_tokens"],
        "temperature": agent_cfg.get("temperature", _DEFAULTS["temperature"]),
    }
