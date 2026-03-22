# AI-Powered Email Assistant

An agentic email drafting system built with [LangGraph](https://github.com/langchain-ai/langgraph) and the [Anthropic Claude API](https://docs.anthropic.com). A pipeline of specialised agents collaborates to parse user intent, apply tone styling, personalise the output, draft an email, review it, and retry if quality falls short.

---

## Features

- **Multi-agent pipeline** — seven focused agents, each with a single responsibility
- **Tone control** — formal, casual, assertive, or empathetic styles
- **Personalisation** — per-user profiles (name, role, company, signature) persisted to disk
- **Self-review loop** — a review agent scores every draft; low-scoring drafts are retried (up to 2 times)
- **Draft logging** — last 50 drafts saved to `src/memory/drafts_log.json`
- **LangSmith tracing** — full node-by-node pipeline traces via LangSmith
- **Docker support** — production-ready multi-stage Docker image with tests run at build time

---

## Project Structure

```
email_assitant/
├── docs/                          # Documentation and reference PDF
│   ├── AI-Powered Email Assistant.pdf
│   ├── agents.md                  # Per-agent reference
│   ├── workflow.md                # State schema & graph topology
│   └── setup.md                  # Installation & configuration
├── src/
│   ├── agents/                    # One file per agent
│   │   ├── input_parser_agent.py
│   │   ├── intent_detection_agent.py
│   │   ├── tone_stylist_agent.py
│   │   ├── personalization_agent.py
│   │   ├── draft_writer_agent.py
│   │   ├── review_agent.py
│   │   └── router_agent.py
│   ├── integrations/
│   │   └── anthropic_client.py    # Shared Claude API wrapper
│   ├── memory/                    # Runtime data (auto-created)
│   │   ├── user_profiles.json
│   │   └── drafts_log.json
│   ├── ui/
│   │   └── streamlit_app.py       # Streamlit web UI
│   └── workflow/
│       ├── state.py               # EmailState TypedDict
│       └── langgraph_flow.py      # Graph definition & compiled app
├── tests/                         # Pytest unit tests (mocked, no API calls)
├── Dockerfile                     # Multi-stage build (test → runtime)
├── docker-compose.yml
├── .env.example                   # Environment variable template
└── README.md
```

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and optionally LANGCHAIN_API_KEY

# 2. Build and run (runs tests inside the build, then starts the app)
docker compose up --build
```

Open **http://localhost:8501** in your browser.

### Option 2 — Local

```bash
# 1. Install dependencies (requires Python 3.11+)
pip install anthropic langgraph streamlit pydantic

# 2. Copy and fill in environment variables
cp .env.example .env

# 3. Run the Streamlit UI
PYTHONPATH=. streamlit run src/ui/streamlit_app.py
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key — get it from [console.anthropic.com](https://console.anthropic.com) |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key — get it from [smith.langchain.com](https://smith.langchain.com) |
| `LANGCHAIN_ENDPOINT` | No | LangSmith endpoint (default: `https://api.smith.langchain.com`) |
| `LANGCHAIN_PROJECT` | No | LangSmith project name (default: `email-assistant`) |

---

## How It Works

```
User prompt
    │
    ▼
input_parser ──► intent_detection ──► tone_stylist ──► personalization
                                                              │
                                                              ▼
                                                        draft_writer
                                                              │
                                                              ▼
                                                           review
                                                              │
                                                         ┌────┴────┐
                                                  retry? │         │ pass
                                                         ▼         ▼
                                                   draft_writer   END
                                                  (up to 2x)
```

See [docs/workflow.md](docs/workflow.md) for the full graph description.

---

## Observability

When `LANGCHAIN_TRACING_V2=true` is set, every workflow run is traced to [LangSmith](https://smith.langchain.com). Each LangGraph node appears as a separate span, giving full visibility into inputs, outputs, latency, and retry behaviour for every email generated.

---

## Running Tests

```bash
# Local
python -m pytest tests/ -v

# Tests also run automatically during docker build (build fails if any test fails)
docker compose build
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/agents.md](docs/agents.md) | What each agent does, its inputs, outputs, and prompts |
| [docs/workflow.md](docs/workflow.md) | `EmailState` schema and LangGraph topology |
| [docs/setup.md](docs/setup.md) | Installation, configuration, and user profiles |
