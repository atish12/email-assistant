# Agents Reference

Each agent lives in `src/agents/` and exposes a single `run(state: EmailState) -> EmailState` function. Agents read from and write to the shared [`EmailState`](workflow.md#emailstate-schema) dict; they do not communicate with each other directly.

---

## 1. Input Parser (`input_parser_agent.py`)

**Purpose:** Validates the raw user prompt and extracts structured metadata.

**Reads from state:** `user_prompt`, `recipient` (optional), `tone` (optional)

**Writes to state:** `recipient`, `tone`, `constraints`, `subject_hint`, `intent_hint`, `errors`

**How it works:**
Sends the user prompt to Claude with a system prompt that instructs it to return a JSON object. Falls back to sensible defaults if JSON parsing fails.

**Claude output schema:**
```json
{
  "recipient":    "string | null",
  "tone_hint":    "formal | casual | assertive | empathetic | null",
  "intent_hint":  "string",
  "constraints":  ["string"],
  "subject_hint": "string | null",
  "error":        "string | null"
}
```

**Notes:**
- State-level `recipient` and `tone` are never overwritten if already set (explicit UI values take priority).
- If `error` is non-null the message is appended to `state["errors"]` and the pipeline continues.

---

## 2. Intent Detection (`intent_detection_agent.py`)

**Purpose:** Classifies the email request into one of nine intent categories.

**Reads from state:** `user_prompt`, `intent_hint`, `recipient`

**Writes to state:** `intent`

**Supported intents:**

| Intent | When to use |
|---|---|
| `outreach` | Cold / first-contact emails |
| `follow_up` | Checking in after a prior interaction |
| `apology` | Expressing regret or addressing a mistake |
| `information` | Sharing facts or updates |
| `meeting_request` | Scheduling a meeting or call |
| `thank_you` | Expressing gratitude |
| `complaint` | Raising a concern or issue |
| `introduction` | Introducing yourself or someone else |
| `other` | Anything that doesn't fit above |

**Claude output schema:**
```json
{
  "intent":     "string",
  "confidence": 0.0–1.0,
  "reasoning":  "string"
}
```

Falls back to `"other"` on JSON parse error or unrecognised intent.

---

## 3. Tone Stylist (`tone_stylist_agent.py`)

**Purpose:** Looks up a pre-defined tone guide and injects it into state. No LLM call — pure lookup.

**Reads from state:** `tone`

**Writes to state:** `tone` (normalised), `tone_guide`

**Tone guide structure:**

```python
{
  "description": str,   # one-line summary
  "vocabulary":  str,   # guidance on word choice
  "greeting":    str,   # suggested salutation
  "closing":     str,   # suggested sign-off
  "avoid":       str,   # phrases / patterns to avoid
}
```

**Supported tones:**

| Tone | Description |
|---|---|
| `formal` | Professional, respectful, structured |
| `casual` | Friendly, warm, conversational |
| `assertive` | Confident, direct, action-oriented |
| `empathetic` | Understanding, supportive, considerate |

Defaults to `formal` for any unrecognised value.

---

## 4. Personalization (`personalization_agent.py`)

**Purpose:** Loads the user's profile from disk and merges it into state so the Draft Writer can personalise the email. No LLM call.

**Reads from state:** `user_id`, `tone`

**Writes to state:** `user_profile`, `tone` (if not already set)

**Profile fields used:**

| Profile key | Used as |
|---|---|
| `name` | Sender name in email |
| `role` | Sender job title |
| `company` | Company name |
| `preferred_tone` | Default tone when none specified |
| `signature` | Custom email sign-off block |
| `drafts_summary` | Recent history hint for the Draft Writer |

**Storage:** `src/memory/user_profiles.json`

To create or update a profile, call `personalization_agent.save_profile(user_id, profile_dict)` directly.

---

## 5. Draft Writer (`draft_writer_agent.py`)

**Purpose:** Generates the full email (subject + body) using all context gathered so far.

**Reads from state:** `intent`, `tone`, `tone_guide`, `user_profile`, `constraints`, `subject_hint`, `user_prompt`, `recipient`, `retry_count`, `review_feedback`

**Writes to state:** `draft`

**How it works:**
Builds a detailed system prompt from the tone guide and profile, then asks Claude to write the email. On retries, the previous reviewer feedback is appended so Claude can address the specific issues.

**Output format expected from Claude:**
```
Subject: <subject line>

<greeting>,

<body paragraphs>

<closing>,
<sender name>
```

**Token budget:** `max_tokens=1024`

---

## 6. Review Agent (`review_agent.py`)

**Purpose:** Scores the draft and decides whether it needs revision.

**Reads from state:** `intent`, `tone`, `constraints`, `user_prompt`, `draft`

**Writes to state:** `review_passed`, `review_score`, `review_feedback`, `subject_hint` (if improved subject suggested)

**Claude output schema:**
```json
{
  "passed":           true | false,
  "score":            1–10,
  "tone_aligned":     true | false,
  "grammar_ok":       true | false,
  "intent_fulfilled": true | false,
  "feedback":         "string",
  "improved_subject": "string | null"
}
```

Falls back to `passed=true, score=7` on JSON parse error (fail-safe).

---

## 7. Router (`router_agent.py`)

**Purpose:** Decides whether to retry the Draft Writer or finalise. Also persists the result.

**Reads from state:** `review_passed`, `retry_count`, `draft`, `intent`, `tone`, `user_prompt`, `review_feedback`, `user_id`

**Writes to state:** `route` (`"retry"` or `"end"`), `retry_count`, `final_email`

**Retry logic:**

| Condition | Route |
|---|---|
| `review_passed == True` | `end` |
| `retry_count >= 2` | `end` (gives up after 2 retries) |
| Otherwise | `retry` |

**Side effects on `"end"`:**
- Appends a record to `src/memory/drafts_log.json` (capped at 50 entries).
- Updates `preferred_tone` and `drafts_summary` in the user's profile.
