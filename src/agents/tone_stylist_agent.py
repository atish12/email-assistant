"""
Tone Stylist Agent
------------------
Builds tone instructions and a style guide based on the selected tone.
Supported tones: formal, casual, assertive, empathetic
"""

from src.workflow.state import EmailState

TONE_GUIDES = {
    "formal": {
        "description": "Professional, respectful, structured",
        "vocabulary": "Use complete sentences, avoid contractions, precise language",
        "greeting": "Dear [Name],",
        "closing": "Sincerely, / Best regards,",
        "avoid": "slang, emojis, overly casual phrasing",
    },
    "casual": {
        "description": "Friendly, warm, conversational",
        "vocabulary": "Contractions are fine, natural flow, approachable",
        "greeting": "Hi [Name], / Hey [Name],",
        "closing": "Thanks! / Cheers, / Best,",
        "avoid": "stiff corporate language, overly formal phrasing",
    },
    "assertive": {
        "description": "Confident, direct, action-oriented",
        "vocabulary": "Clear calls to action, minimal hedging, decisive statements",
        "greeting": "Hi [Name],",
        "closing": "Looking forward to your response, / Best,",
        "avoid": "passive voice, apologetic language, excessive qualifiers",
    },
    "empathetic": {
        "description": "Understanding, supportive, considerate",
        "vocabulary": "Acknowledge feelings, use 'I understand', show care",
        "greeting": "Dear [Name], / Hi [Name],",
        "closing": "Warmly, / With appreciation,",
        "avoid": "blunt statements, dismissive language",
    },
}

DEFAULT_TONE = "formal"


def run(state: EmailState) -> EmailState:
    tone = (state.tone or DEFAULT_TONE).lower()
    if tone not in TONE_GUIDES:
        tone = DEFAULT_TONE

    state.tone = tone
    state.tone_guide = TONE_GUIDES[tone]

    return state
