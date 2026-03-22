"""
Draft Writer Agent
------------------
Generates the main email body using the extracted intent, tone guide,
personalization data, and any constraints.
"""

from src.integrations.anthropic_client import call_claude
from src.integrations.config_loader import get_agent_config
from src.workflow.state import EmailState

_CFG = get_agent_config("draft_writer")


def build_system_prompt(state: EmailState) -> str:
    tone = state.tone or "formal"
    tone_guide = state.tone_guide
    profile = state.user_profile
    intent = state.intent or "other"
    constraints = state.constraints

    profile_section = ""
    if profile.get("sender_name"):
        profile_section += f"\nSender name: {profile['sender_name']}"
    if profile.get("sender_role"):
        profile_section += f"\nSender role: {profile['sender_role']}"
    if profile.get("company"):
        profile_section += f"\nCompany: {profile['company']}"
    if profile.get("custom_signature"):
        profile_section += f"\nSignature to use: {profile['custom_signature']}"

    constraints_section = ""
    if constraints:
        constraints_section = "\nConstraints to follow:\n" + "\n".join(
            f"- {c}" for c in constraints
        )

    retry_note = ""
    if state.retry_count > 0 and state.review_feedback:
        retry_note = f"\n\nPrevious draft had issues. Reviewer feedback:\n{state.review_feedback}\nPlease address these in this new draft."

    return f"""You are a professional email drafting agent.

Write a complete, polished email for the following:
- Intent: {intent}
- Tone: {tone} — {tone_guide.get('description', '')}
- Tone vocabulary: {tone_guide.get('vocabulary', '')}
- Suggested greeting style: {tone_guide.get('greeting', '')}
- Suggested closing style: {tone_guide.get('closing', '')}
- Words/phrases to avoid: {tone_guide.get('avoid', '')}
{profile_section}
{constraints_section}
{retry_note}

Output format:
Subject: <subject line>

<email body with greeting, paragraphs, and closing>

Write only the email. No explanations or meta-commentary."""


def run(state: EmailState) -> EmailState:
    system_prompt = build_system_prompt(state)

    user_message = f"""User request: {state.user_prompt}
Recipient: {state.recipient or 'the recipient'}
Subject hint: {state.subject_hint or ''}"""

    draft = call_claude(system_prompt, user_message, **_CFG)
    state.draft = draft
    return state
