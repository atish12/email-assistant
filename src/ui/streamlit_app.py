import os
import base64
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

from src.workflow.langgraph_flow import run_email_workflow
from src.agents.personalization_agent import load_profiles, save_profile

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
        "\u2014": "--",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "-",
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
                display: inline-block;
                padding: 8px 16px;
                font-size: 14px;
                text-decoration: none;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 6px;
                background: #fff;
                margin-right: 8px;
                cursor: pointer;
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
            "name":      sender_name,
            "role":      sender_role,
            "company":   company,
            "signature": signature,
        })
        st.success("Profile saved!")

    st.divider()
    st.caption("Profile is used to personalise every email you generate.")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("✉️ AI Email Assistant")
st.caption("Describe the email you need — the assistant will draft, review, and refine it for you.")

st.divider()

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
        options=["auto-detect", "outreach", "follow_up", "apology", "information", "meeting_request", "thank_you", "complaint", "introduction", "other"],
        index=0,
        help="Select the email intent or let the agent detect it automatically.",
    )
    tone = st.selectbox(
        "Tone",
        options=["formal", "casual", "assertive", "empathetic"],
        index=0,
    )

generate = st.button("✨ Generate Email", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Generation — store result in session_state so download buttons survive reruns
# ---------------------------------------------------------------------------

if generate:
    if not user_prompt.strip():
        st.warning("Please describe the email you want to write.")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set. Add it to your environment before running.")
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

# ---------------------------------------------------------------------------
# Output — rendered on every rerun as long as result is in session_state
# ---------------------------------------------------------------------------

if "result" in st.session_state:
    result = st.session_state["result"]
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
