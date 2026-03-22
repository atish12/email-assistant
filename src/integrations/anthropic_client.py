import os
import anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"


def call_claude(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model: str = DEFAULT_MODEL,
    fallback_model: str | None = None,
) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def _call(m: str) -> str:
        response = client.messages.create(
            model=m,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""

    try:
        return _call(model)
    except anthropic.APIStatusError as e:
        if fallback_model and fallback_model != model and e.status_code in (429, 529):
            return _call(fallback_model)
        raise
