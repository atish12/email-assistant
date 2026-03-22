from typing import Any, Optional

from pydantic import BaseModel, Field


class EmailState(BaseModel):
    model_config = {"frozen": False}

    # User inputs
    user_prompt: str = ""
    recipient: Optional[str] = None
    tone: Optional[str] = None          # formal | casual | assertive | empathetic
    user_id: str = "default"

    # Parsed / detected fields
    intent: Optional[str] = None
    intent_hint: Optional[str] = None
    subject_hint: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)

    # Tone guide (populated by ToneStylistAgent)
    tone_guide: dict[str, Any] = Field(default_factory=dict)

    # Personalization
    user_profile: dict[str, Any] = Field(default_factory=dict)

    # Draft fields
    draft: Optional[str] = None
    final_email: Optional[str] = None

    # Review fields
    review_passed: bool = False
    review_score: Optional[int] = None
    review_feedback: Optional[str] = None

    # Routing
    route: Optional[str] = None         # "retry" | "end"
    retry_count: int = 0

    # Error tracking
    errors: list[str] = Field(default_factory=list)
