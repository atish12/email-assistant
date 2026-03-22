"""
Tests for src/agents/tone_stylist_agent.py
(No LLM call — pure lookup logic.)
"""

import pytest

from src.agents import tone_stylist_agent
from src.agents.tone_stylist_agent import TONE_GUIDES, DEFAULT_TONE
from src.workflow.state import EmailState

SUPPORTED_TONES = list(TONE_GUIDES.keys())
EXPECTED_GUIDE_KEYS = {"description", "vocabulary", "greeting", "closing", "avoid"}


# ---------------------------------------------------------------------------
# Each supported tone sets the correct guide
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tone", SUPPORTED_TONES)
def test_known_tone_sets_guide(base_state, tone):
    base_state.tone = tone
    result = tone_stylist_agent.run(base_state)

    assert result.tone == tone
    assert result.tone_guide == TONE_GUIDES[tone]


@pytest.mark.parametrize("tone", SUPPORTED_TONES)
def test_tone_guide_has_all_keys(base_state, tone):
    base_state.tone = tone
    result = tone_stylist_agent.run(base_state)

    assert EXPECTED_GUIDE_KEYS.issubset(result.tone_guide.keys())


# ---------------------------------------------------------------------------
# Unknown / missing tone defaults to "formal"
# ---------------------------------------------------------------------------

def test_unknown_tone_defaults_to_formal(base_state):
    base_state.tone = "pirate"
    result = tone_stylist_agent.run(base_state)

    assert result.tone == DEFAULT_TONE
    assert result.tone_guide == TONE_GUIDES[DEFAULT_TONE]


def test_missing_tone_defaults_to_formal(base_state):
    base_state.tone = None
    result = tone_stylist_agent.run(base_state)

    assert result.tone == DEFAULT_TONE


# ---------------------------------------------------------------------------
# Tone normalised to lowercase
# ---------------------------------------------------------------------------

def test_tone_normalised_to_lowercase(base_state):
    base_state.tone = "CASUAL"
    result = tone_stylist_agent.run(base_state)

    assert result.tone == "casual"
    assert result.tone_guide == TONE_GUIDES["casual"]
