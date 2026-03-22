"""
Routing & Memory Agent
----------------------
Decides whether to finalize the draft or retry the draft writer.
Also saves the draft and user feedback to the memory/profile store.
"""

import json
import os
from datetime import datetime
from src.workflow.state import EmailState
from src.agents.personalization_agent import load_profiles, save_profile

MAX_RETRIES = 2

DRAFTS_LOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "drafts_log.json"
)


def log_draft(state: EmailState) -> None:
    try:
        if os.path.exists(DRAFTS_LOG_PATH):
            with open(DRAFTS_LOG_PATH, "r") as f:
                logs = json.load(f)
        else:
            logs = []
    except (json.JSONDecodeError, FileNotFoundError):
        logs = []

    logs.append(
        {
            "timestamp": datetime.now().isoformat(),
            "user_id": state.user_id,
            "intent": state.intent,
            "tone": state.tone,
            "prompt": state.user_prompt,
            "draft": state.draft,
            "score": state.review_score,
        }
    )

    os.makedirs(os.path.dirname(DRAFTS_LOG_PATH), exist_ok=True)
    with open(DRAFTS_LOG_PATH, "w") as f:
        json.dump(logs[-50:], f, indent=2)  # keep last 50 drafts


def should_retry(state: EmailState) -> bool:
    if state.review_passed:
        return False
    if state.retry_count >= MAX_RETRIES:
        return False
    return True


def run(state: EmailState) -> EmailState:
    if should_retry(state):
        state.retry_count = state.retry_count + 1
        state.route = "retry"
        return state

    # Finalize: use the draft as the final email
    state.final_email = state.draft or ""
    state.route = "end"

    # Log the draft
    log_draft(state)

    # Update user profile with preferred tone
    profiles = load_profiles()
    profile = profiles.get(state.user_id, {})
    if state.tone:
        profile["preferred_tone"] = state.tone
    recent = profile.get("drafts_summary", "")
    profile["drafts_summary"] = (
        f"Last intent: {state.intent}, tone: {state.tone}. {recent}"
    )[:300]
    save_profile(state.user_id, profile)

    return state
