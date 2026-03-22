# Workflow Reference

## Graph Topology

The workflow is defined in `src/workflow/langgraph_flow.py` using a LangGraph `StateGraph`.

```
┌─────────────┐
│ input_parser│  ← entry point
└──────┬──────┘
       │
┌──────▼──────────┐
│intent_detection │
└──────┬──────────┘
       │
┌──────▼──────┐
│ tone_stylist│
└──────┬──────┘
       │
┌──────▼────────────┐
│  personalization  │
└──────┬────────────┘
       │
┌──────▼───────┐  ◄──────────────────┐
│ draft_writer │                     │ route = "retry"
└──────┬───────┘                     │
       │                             │
┌──────▼──────┐                      │
│   review    │                      │
└──────┬──────┘                      │
       │                             │
┌──────▼──────┐                      │
│   router    │ ─── route = "end" ──► END
└─────────────┘
```

The retry loop runs at most **2 times** (`MAX_RETRIES = 2` in `router_agent.py`).

---

## EmailState Schema

Defined in `src/workflow/state.py` as a `TypedDict` with `total=False` (all fields optional at construction time).

### User inputs

| Field | Type | Description |
|---|---|---|
| `user_prompt` | `str` | Raw request from the user |
| `recipient` | `str \| None` | Name or role of the email recipient |
| `tone` | `str \| None` | Requested tone (`formal`, `casual`, `assertive`, `empathetic`) |
| `user_id` | `str \| None` | Profile identifier; defaults to `"default"` |

### Parsed / detected fields

| Field | Type | Set by |
|---|---|---|
| `intent` | `str \| None` | `intent_detection_agent` |
| `intent_hint` | `str \| None` | `input_parser_agent` |
| `subject_hint` | `str \| None` | `input_parser_agent`, `review_agent` |
| `constraints` | `list[str]` | `input_parser_agent` |

### Tone & personalisation

| Field | Type | Set by |
|---|---|---|
| `tone_guide` | `dict` | `tone_stylist_agent` |
| `user_profile` | `dict` | `personalization_agent` |

### Draft fields

| Field | Type | Set by |
|---|---|---|
| `draft` | `str \| None` | `draft_writer_agent` |
| `final_email` | `str \| None` | `router_agent` (on `"end"`) |

### Review fields

| Field | Type | Set by |
|---|---|---|
| `review_passed` | `bool` | `review_agent` |
| `review_score` | `int \| None` | `review_agent` (1–10) |
| `review_feedback` | `str \| None` | `review_agent` |

### Routing & errors

| Field | Type | Description |
|---|---|---|
| `route` | `str \| None` | `"retry"` or `"end"` — set by `router_agent` |
| `retry_count` | `int` | Number of retries so far |
| `errors` | `list[str]` | Non-fatal error messages accumulated during the run |

---

## Running the Workflow

### Python API

```python
from src.workflow.langgraph_flow import run_email_workflow

result = run_email_workflow(
    user_prompt="Write a thank-you email after our product demo",
    recipient="Emily Chen",
    tone="casual",
    user_id="bob",
)

print(result["final_email"])
print(f"Review score: {result['review_score']}")
print(f"Retries: {result['retry_count']}")
```

### Using the compiled app directly

```python
from src.workflow.langgraph_flow import app

state = app.invoke({
    "user_prompt": "...",
    "errors": [],
    "constraints": [],
    "retry_count": 0,
    "review_passed": False,
})
```

### Streaming node-by-node

```python
from src.workflow.langgraph_flow import app

for step in app.stream({"user_prompt": "...", "errors": [], "constraints": [], "retry_count": 0, "review_passed": False}):
    node_name, node_state = next(iter(step.items()))
    print(f"[{node_name}] intent={node_state.get('intent')} score={node_state.get('review_score')}")
```

---

## Memory Files

| File | Created by | Contents |
|---|---|---|
| `src/memory/user_profiles.json` | `personalization_agent` | Per-user profile dicts keyed by `user_id` |
| `src/memory/drafts_log.json` | `router_agent` | Last 50 completed draft records |

Both files are created automatically on first write. The `src/memory/` directory is created if it does not exist.
