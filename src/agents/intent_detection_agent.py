"""
Intent Detection Agent
----------------------
Classifies the email intent into one of the standard categories:
outreach, follow_up, apology, information, meeting_request,
thank_you, complaint, introduction, or other.
"""

import json
from src.integrations.anthropic_client import call_claude
from src.integrations.config_loader import get_agent_config
from src.workflow.state import EmailState

_CFG = get_agent_config("intent_detection")

INTENTS = [
    "outreach",
    "follow_up",
    "apology",
    "information",
    "meeting_request",
    "thank_you",
    "complaint",
    "introduction",
    "other",
]

SYSTEM_PROMPT = f"""You are an intent classification agent for an AI email assistant.
Classify the user's email request into exactly one of these intents:
{', '.join(INTENTS)}

Return a valid JSON object with:
- "intent": the classified intent (one of the list above)
- "confidence": float between 0 and 1
- "reasoning": one sentence explaining the classification

Return ONLY the JSON object, no extra text."""


def run(state: EmailState) -> EmailState:
    # If intent was explicitly set by the user, skip detection
    if state.intent and state.intent in INTENTS:
        return state

    user_message = f"""User prompt: {state.user_prompt}
Intent hint: {state.intent_hint or ''}
Recipient: {state.recipient or 'unknown'}"""

    response = call_claude(SYSTEM_PROMPT, user_message, **_CFG)

    try:
        result = json.loads(response)
        intent = result.get("intent", "other")
        if intent not in INTENTS:
            intent = "other"
        state.intent = intent
    except json.JSONDecodeError:
        state.intent = "other"

    return state
