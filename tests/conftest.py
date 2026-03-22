"""
Shared fixtures for all agent tests.
"""

import pytest
from src.workflow.state import EmailState


@pytest.fixture
def base_state():
    """Minimal valid EmailState for use as a starting point."""
    return EmailState(
        user_prompt="Write a follow-up email to my client about the project.",
        user_id="test_user",
    )
