"""
Input Parsing Agent
-------------------
Validates the user prompt and extracts structured fields:
recipient, tone preference, intent hints, and any constraints.
"""

import json
from src.integrations.anthropic_client import call_claude
from src.integrations.config_loader import get_agent_config
from src.workflow.state import EmailState

_CFG = get_agent_config("input_parser")

SYSTEM_PROMPT = """You are an input parsing agent for an AI email assistant.
Your job is to extract structured information from the user's raw prompt.

Return a valid JSON object with these keys:
- "recipient": name or role of the email recipient (string, or null if unknown)
- "tone_hint": suggested tone (one of: formal, casual, assertive, empathetic, or null)
- "intent_hint": brief description of what the email should accomplish (string)
- "constraints": list of specific requirements mentioned (e.g., "keep it short", "include meeting link")
- "subject_hint": a suggested email subject line (string or null)
- "error": null if valid, or a string describing why the prompt is invalid

Return ONLY the JSON object, no extra text."""


def run(state: EmailState) -> EmailState:
    user_input = f"User prompt: {state.user_prompt}"
    if state.recipient:
        user_input += f"\nRecipient context: {state.recipient}"

    response = call_claude(SYSTEM_PROMPT, user_input, **_CFG)

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        parsed = {
            "recipient": None,
            "tone_hint": None,
            "intent_hint": state.user_prompt,
            "constraints": [],
            "subject_hint": None,
            "error": None,
        }

    if parsed.get("error"):
        state.errors.append(f"Input parsing error: {parsed['error']}")

    if not state.recipient and parsed.get("recipient"):
        state.recipient = parsed["recipient"]
    if not state.tone and parsed.get("tone_hint"):
        state.tone = parsed["tone_hint"]

    state.constraints = parsed.get("constraints", [])
    state.subject_hint = parsed.get("subject_hint")
    state.intent_hint = parsed.get("intent_hint", state.user_prompt)

    return state
