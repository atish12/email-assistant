"""
LangGraph Workflow
-----------------
Wires all agents into a StateGraph:

  input_parser → intent_detection → tone_stylist → personalization
      → draft_writer → review → router
                                    │
                     ┌──────────────┘
                     │  route == "retry"  → draft_writer (loop)
                     │  route == "end"    → END
"""

from langgraph.graph import StateGraph, END

from src.workflow.state import EmailState
from src.agents import (
    input_parser_agent,
    intent_detection_agent,
    tone_stylist_agent,
    personalization_agent,
    draft_writer_agent,
    review_agent,
    router_agent,
)


# ---------------------------------------------------------------------------
# Node wrappers
# ---------------------------------------------------------------------------

def node_input_parser(state: EmailState) -> EmailState:
    return input_parser_agent.run(state)


def node_intent_detection(state: EmailState) -> EmailState:
    return intent_detection_agent.run(state)


def node_tone_stylist(state: EmailState) -> EmailState:
    return tone_stylist_agent.run(state)


def node_personalization(state: EmailState) -> EmailState:
    return personalization_agent.run(state)


def node_draft_writer(state: EmailState) -> EmailState:
    return draft_writer_agent.run(state)


def node_review(state: EmailState) -> EmailState:
    return review_agent.run(state)


def node_router(state: EmailState) -> EmailState:
    return router_agent.run(state)


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def route_after_router(state: EmailState) -> str:
    """Return the next node name based on router decision."""
    return state.route or "end"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(EmailState)

    graph.add_node("input_parser", node_input_parser)
    graph.add_node("intent_detection", node_intent_detection)
    graph.add_node("tone_stylist", node_tone_stylist)
    graph.add_node("personalization", node_personalization)
    graph.add_node("draft_writer", node_draft_writer)
    graph.add_node("review", node_review)
    graph.add_node("router", node_router)

    graph.set_entry_point("input_parser")

    graph.add_edge("input_parser", "intent_detection")
    graph.add_edge("intent_detection", "tone_stylist")
    graph.add_edge("tone_stylist", "personalization")
    graph.add_edge("personalization", "draft_writer")
    graph.add_edge("draft_writer", "review")
    graph.add_edge("review", "router")

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "retry": "draft_writer",
            "end": END,
        },
    )

    return graph


# ---------------------------------------------------------------------------
# Compiled app (import this in your entry point)
# ---------------------------------------------------------------------------

app = build_graph().compile()


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

def run_email_workflow(
    user_prompt: str,
    recipient: str | None = None,
    tone: str | None = None,
    intent: str | None = None,
    user_id: str = "default",
) -> EmailState:
    """Run the full email generation workflow and return the final state."""
    initial_state = EmailState(
        user_prompt=user_prompt,
        recipient=recipient,
        tone=tone,
        intent=intent if intent and intent != "auto-detect" else None,
        user_id=user_id,
    )
    result = app.invoke(initial_state)
    if isinstance(result, dict):
        return EmailState(**result)
    return result
