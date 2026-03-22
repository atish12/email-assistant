"""
Personalization Agent
---------------------
Loads user profile data (name, company, role, writing style preferences)
and injects it into the state so the Draft Writer can personalize the email.
"""

import json
import os
from src.workflow.state import EmailState

PROFILES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "memory", "user_profiles.json"
)


def load_profiles() -> dict:
    try:
        with open(PROFILES_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_profile(user_id: str, profile: dict) -> None:
    profiles = load_profiles()
    profiles[user_id] = profile
    os.makedirs(os.path.dirname(PROFILES_PATH), exist_ok=True)
    with open(PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)


def run(state: EmailState) -> EmailState:
    profiles = load_profiles()
    profile = profiles.get(state.user_id, {})

    # Merge: state-level overrides take priority over stored profile
    merged = {
        "sender_name": profile.get("name", ""),
        "sender_role": profile.get("role", ""),
        "company": profile.get("company", ""),
        "preferred_tone": profile.get("preferred_tone", state.tone or "formal"),
        "custom_signature": profile.get("signature", ""),
        "previous_drafts_summary": profile.get("drafts_summary", ""),
    }

    # Don't override explicit tone choice from UI
    if not state.tone and merged["preferred_tone"]:
        state.tone = merged["preferred_tone"]

    state.user_profile = merged
    return state
