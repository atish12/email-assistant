# Setup & Configuration

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

## Installation

```bash
# Clone / open the project
cd email_assitant

# Install dependencies
pip install anthropic langgraph
```

> The project has no `requirements.txt` yet. To generate one:
> ```bash
> pip freeze > requirements.txt
> ```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |

```bash
# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Model

The Claude model is configured in `src/integrations/anthropic_client.py`:

```python
MODEL = "claude-sonnet-4-6"
```

Change this to any supported Claude model (e.g. `"claude-opus-4-6"`) before running.

---

## User Profiles

Profiles are stored in `src/memory/user_profiles.json` and keyed by `user_id`. You can seed a profile manually:

```python
from src.agents.personalization_agent import save_profile

save_profile("alice", {
    "name": "Alice Johnson",
    "role": "Product Manager",
    "company": "Acme Corp",
    "preferred_tone": "formal",
    "signature": "Best regards,\nAlice Johnson\nProduct Manager, Acme Corp",
})
```

Or let the system build the profile automatically — after each completed draft the router updates `preferred_tone` and `drafts_summary` for the given `user_id`.

**Profile fields:**

| Key | Type | Description |
|---|---|---|
| `name` | `str` | Sender's full name |
| `role` | `str` | Sender's job title |
| `company` | `str` | Sender's company |
| `preferred_tone` | `str` | Default tone when none is specified |
| `signature` | `str` | Custom sign-off block |
| `drafts_summary` | `str` | Auto-updated summary of recent drafts (max 300 chars) |

---

## Project Layout

```
src/
├── agents/
│   ├── __init__.py
│   ├── input_parser_agent.py
│   ├── intent_detection_agent.py
│   ├── tone_stylist_agent.py
│   ├── personalization_agent.py
│   ├── draft_writer_agent.py
│   ├── review_agent.py
│   └── router_agent.py
├── integrations/
│   ├── __init__.py
│   └── anthropic_client.py      ← MODEL and call_claude() live here
├── memory/                       ← auto-created at runtime
│   ├── user_profiles.json
│   └── drafts_log.json
└── workflow/
    ├── __init__.py
    ├── state.py                  ← EmailState TypedDict
    └── langgraph_flow.py         ← graph definition + run_email_workflow()
```

---

## Extending the Pipeline

### Add a new tone

Edit `TONE_GUIDES` in `src/agents/tone_stylist_agent.py`:

```python
TONE_GUIDES["persuasive"] = {
    "description": "Motivating, benefit-focused, compelling",
    "vocabulary":  "Use action verbs, highlight benefits, create urgency",
    "greeting":    "Hi [Name],",
    "closing":     "Looking forward to hearing from you,",
    "avoid":       "passive constructions, negative framing",
}
```

### Add a new intent

Append to the `INTENTS` list in `src/agents/intent_detection_agent.py`:

```python
INTENTS = [
    ...,
    "negotiation",   # ← new
]
```

### Adjust retry limit

Change `MAX_RETRIES` in `src/agents/router_agent.py`:

```python
MAX_RETRIES = 3   # default is 2
```
