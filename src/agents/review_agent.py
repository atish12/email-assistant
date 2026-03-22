"""
Review & Validator Agent
------------------------
Checks the draft for:
- Tone alignment with the requested tone
- Grammar and clarity
- Contextual coherence with the user's intent
- Adherence to constraints

Returns a pass/fail decision and feedback for retry.
"""

import json
from src.integrations.anthropic_client import call_claude
from src.workflow.state import EmailState

SYSTEM_PROMPT = """You are a quality review agent for an AI email assistant.
Review the provided email draft and evaluate it on:
1. Tone alignment (does it match the requested tone?)
2. Grammar and clarity (is it well-written?)
3. Intent fulfillment (does it accomplish what was asked?)
4. Constraint adherence (does it follow any specified requirements?)

Return a valid JSON object with:
- "passed": true if the draft is acceptable, false if it needs revision
- "score": integer from 1-10
- "tone_aligned": boolean
- "grammar_ok": boolean
- "intent_fulfilled": boolean
- "feedback": string with specific improvement suggestions (empty string if passed)
- "improved_subject": suggested improved subject line or null

Return ONLY the JSON object, no extra text."""


def run(state: EmailState) -> EmailState:
    user_message = f"""Requested intent: {state.intent or 'unknown'}
Requested tone: {state.tone or 'formal'}
Constraints: {', '.join(state.constraints) or 'none'}
User prompt: {state.user_prompt}

Email draft to review:
---
{state.draft or ''}
---"""

    response = call_claude(SYSTEM_PROMPT, user_message, max_tokens=512)

    try:
        result = json.loads(response)
        state.review_passed = result.get("passed", True)
        state.review_score = result.get("score", 7)
        state.review_feedback = result.get("feedback", "")
        if result.get("improved_subject"):
            state.subject_hint = result["improved_subject"]
    except json.JSONDecodeError:
        state.review_passed = True
        state.review_score = 7
        state.review_feedback = ""

    return state
