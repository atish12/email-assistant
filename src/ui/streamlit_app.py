import os
import sys
import json
import base64

# Ensure project root is on the path (required for Streamlit Cloud)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

# Load secrets into env vars (Streamlit Cloud stores secrets in st.secrets)
try:
    for _key in ["ANTHROPIC_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2",
                 "LANGCHAIN_ENDPOINT", "LANGCHAIN_PROJECT"]:
        if _key not in os.environ:
            _val = st.secrets.get(_key)
            if _val:
                os.environ[_key] = str(_val)
except Exception:
    pass
import streamlit.components.v1 as components
from fpdf import FPDF

from src.workflow.langgraph_flow import run_email_workflow
from src.agents.personalization_agent import load_profiles, save_profile

DRAFTS_LOG_PATH = os.environ.get(
    "DRAFTS_LOG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "drafts_log.json"),
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Email Assistant",
    page_icon="✉️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    replacements = {
        "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ", "\u2022": "-",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(email_text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.set_margins(20, 20, 20)
    pdf.multi_cell(0, 7, _normalize_text(email_text))
    return bytes(pdf.output())


def download_links(txt: str, pdf: bytes) -> None:
    txt_b64 = base64.b64encode(txt.encode("utf-8")).decode()
    pdf_b64 = base64.b64encode(pdf).decode()
    components.html(
        f"""
        <style>
            .dl-btn {{
                display: inline-block; padding: 8px 16px; font-size: 14px;
                text-decoration: none; color: #333; border: 1px solid #ccc;
                border-radius: 6px; background: #fff; margin-right: 8px; cursor: pointer;
            }}
            .dl-btn:hover {{ background: #f0f0f0; }}
        </style>
        <a class="dl-btn" href="data:text/plain;base64,{txt_b64}" download="email_draft.txt">⬇️ Download .txt</a>
        <a class="dl-btn" href="data:application/pdf;base64,{pdf_b64}" download="email_draft.pdf">⬇️ Download PDF</a>
        """,
        height=52,
    )


def copy_to_clipboard_button(text: str) -> None:
    safe = text.replace("\\", "\\\\").replace("`", "'").replace("\n", "\\n")
    components.html(
        f"""
        <button onclick="navigator.clipboard.writeText(`{safe}`);this.innerText='✅ Copied!';"
                style="padding:8px 18px;font-size:14px;cursor:pointer;border:1px solid #ccc;
                       border-radius:6px;background:#fff;">
            📋 Copy to Clipboard
        </button>
        """,
        height=48,
    )


def load_drafts() -> list:
    try:
        if os.path.exists(DRAFTS_LOG_PATH):
            with open(DRAFTS_LOG_PATH, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return []

# ---------------------------------------------------------------------------
# Sidebar — user profile
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("👤 Your Profile")
    user_id = st.text_input("User ID", value="default", help="Unique identifier for your profile")

    profiles = load_profiles()
    profile = profiles.get(user_id, {})

    sender_name = st.text_input("Your Name", value=profile.get("name", ""))
    sender_role = st.text_input("Your Role", value=profile.get("role", ""))
    company     = st.text_input("Company",   value=profile.get("company", ""))
    signature   = st.text_area("Signature",  value=profile.get("signature", ""), height=80)

    if st.button("💾 Save Profile"):
        save_profile(user_id, {
            "name": sender_name, "role": sender_role,
            "company": company, "signature": signature,
        })
        st.success("Profile saved!")

    st.divider()
    st.caption("Profile is used to personalise every email you generate.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

st.title("✉️ AI Email Assistant")
st.caption("Describe the email you need — the assistant will draft, review, and refine it for you.")
st.divider()

tab_generate, tab_history = st.tabs(["✍️ Generate", "📜 Draft History"])

# ===========================================================================
# TAB 1 — Generate
# ===========================================================================

with tab_generate:
    col1, col2 = st.columns([2, 1])

    with col1:
        user_prompt = st.text_area(
            "What would you like to write?",
            placeholder="e.g. Write a follow-up email to my client about the delayed project milestone...",
            height=140,
        )

    with col2:
        recipient = st.text_input(
            "Recipient",
            placeholder="e.g. John Smith / The hiring manager",
        )
        intent = st.selectbox(
            "Intent",
            options=["auto-detect", "outreach", "follow_up", "apology", "information",
                     "meeting_request", "thank_you", "complaint", "introduction", "other"],
            index=0,
            help="Select the email intent or let the agent detect it automatically.",
        )
        tone = st.selectbox(
            "Tone",
            options=["formal", "casual", "assertive", "empathetic"],
            index=0,
        )

    col_gen, col_reset = st.columns([4, 1])
    with col_gen:
        generate = st.button("✨ Generate Email", type="primary", use_container_width=True)
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            for key in ["result", "email_txt", "email_pdf"]:
                st.session_state.pop(key, None)
            st.rerun()

    # --- Generation ---
    if generate:
        errors = []
        if not user_prompt.strip():
            errors.append("Please describe the email you want to write.")
        if not recipient.strip():
            errors.append("Please enter a recipient.")
        if errors:
            for msg in errors:
                st.warning(msg)
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY is not set. Add it via Streamlit Cloud Secrets or your .env file.")
        else:
            with st.spinner("Agents are working on your email…"):
                try:
                    result = run_email_workflow(
                        user_prompt=user_prompt,
                        recipient=recipient or None,
                        tone=tone,
                        intent=intent,
                        user_id=user_id,
                    )
                    email_text = result.final_email or ""
                    st.session_state["result"] = result
                    st.session_state["email_txt"] = email_text
                    st.session_state["email_pdf"] = generate_pdf(email_text)
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
                    st.stop()

    # --- Output ---
    if "result" in st.session_state:
        result     = st.session_state["result"]
        email_text = st.session_state["email_txt"]
        email_pdf  = st.session_state["email_pdf"]

        st.divider()
        st.subheader("📧 Generated Email")

        st.text_area(
            label="Email Draft",
            value=email_text,
            height=320,
            key="output_email",
            label_visibility="collapsed",
        )

        download_links(email_text, email_pdf)
        copy_to_clipboard_button(email_text)

        st.divider()
        st.subheader("🔍 Pipeline Details")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Intent",       result.intent or "—")
        m2.metric("Tone",         result.tone   or "—")
        m3.metric("Review Score", f"{result.review_score}/10" if result.review_score else "—")
        m4.metric("Retries",      result.retry_count)

        if result.errors:
            with st.expander("⚠️ Warnings"):
                for err in result.errors:
                    st.warning(err)

        if result.review_feedback:
            with st.expander("💬 Reviewer Feedback"):
                st.info(result.review_feedback)

# ===========================================================================
# TAB 2 — Draft History
# ===========================================================================

with tab_history:
    drafts = load_drafts()

    if not drafts:
        st.info("No drafts yet. Generate your first email to see history here.")
    else:
        # Filter by current user
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            filter_user = st.checkbox("Show only my drafts", value=True)
        with col_f2:
            filter_intent = st.selectbox(
                "Filter by intent",
                ["all"] + list({d.get("intent", "—") for d in drafts if d.get("intent")}),
            )
        with col_f3:
            filter_tone = st.selectbox(
                "Filter by tone",
                ["all"] + list({d.get("tone", "—") for d in drafts if d.get("tone")}),
            )

        filtered = list(reversed(drafts))  # newest first
        if filter_user:
            filtered = [d for d in filtered if d.get("user_id") == user_id]
        if filter_intent != "all":
            filtered = [d for d in filtered if d.get("intent") == filter_intent]
        if filter_tone != "all":
            filtered = [d for d in filtered if d.get("tone") == filter_tone]

        st.caption(f"Showing {len(filtered)} draft(s)")
        st.divider()

        for i, draft in enumerate(filtered):
            ts = draft.get("timestamp", "")[:19].replace("T", " ")
            score = draft.get("score")
            label = f"**{ts}** · {draft.get('intent', '—')} · {draft.get('tone', '—')} · Score: {score}/10 if {score} else '—'"
            label = f"**{ts}** &nbsp;|&nbsp; intent: `{draft.get('intent','—')}` &nbsp;|&nbsp; tone: `{draft.get('tone','—')}` &nbsp;|&nbsp; score: `{score}/10`"

            with st.expander(f"📧 {ts}  •  {draft.get('intent','—')}  •  {draft.get('tone','—')}  •  score {score}/10"):
                st.caption(f"**Prompt:** {draft.get('prompt','')}")
                st.text_area(
                    label="Draft",
                    value=draft.get("draft", ""),
                    height=260,
                    key=f"hist_{i}",
                    label_visibility="collapsed",
                )
                draft_txt = draft.get("draft", "")
                draft_pdf = generate_pdf(draft_txt)
                download_links(draft_txt, draft_pdf)
                copy_to_clipboard_button(draft_txt)
