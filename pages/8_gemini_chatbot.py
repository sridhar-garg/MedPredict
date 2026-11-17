"""Streamlit MedPredict Gemini 3.8 Flash chatbot page."""
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="MedPredict AI Assistant | Gemini 3.8 Flash",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)


from sidebar_compat import show_sidebar
show_sidebar()

from health_assistant import (
    MAX_USER_CHARS,
    DEFAULT_MODEL,
    bounded_history,
    friendly_error,
    generate_reply,
    load_settings,
)

try:
    from utils import apply_custom_css
    apply_custom_css()
except ImportError:
    pass

if not st.session_state.get("is_logged_in", False):
    st.warning("Please log in on the Dashboard before using MedPredict AI.")
    st.page_link("app.py", label="Return to login", icon="🏠")
    st.stop()

st.title("💬 MedPredict AI Assistant")
st.caption("Powered by Gemini 3.8 Flash · Educational health and research Q&A")
st.info(
    "This chatbot provides general educational information, not a medical diagnosis. "
    "Do not paste names, contact details, identifiable health records, or private patient information. "
    "Messages you send are processed by Google's Gemini API."
)

key, model = load_settings(Path(__file__).resolve().parents[1], st.secrets)
if not key:
    st.error("Gemini is not configured. Add GEMINI_API_KEY to the project's .env or Streamlit Secrets.")
    with st.expander("Show setup example"):
        st.code('GEMINI_API_KEY=your_api_key_here\nGEMINI_MODEL=gemini-3.8-flash', language="ini")
    st.stop()

st.caption(f"AI model: `{model}`")

account_id = st.session_state.get("user_id") or st.session_state.get("user_email")
if st.session_state.get("medpredict_gemini_account") != account_id:
    st.session_state.medpredict_gemini_account = account_id
    st.session_state.medpredict_gemini_messages = []
if "medpredict_gemini_messages" not in st.session_state:
    st.session_state.medpredict_gemini_messages = []

left, right = st.columns([4, 1])
with left:
    st.markdown("**Ask about medical terminology, public research, or the limitations of AI models.**")
with right:
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.medpredict_gemini_messages = []
        st.rerun()

messages = st.session_state.medpredict_gemini_messages
if not messages:
    st.markdown("Try: *'What is AUROC in medical AI?'* or *'Explain the difference between CT and MRI.'*")

for entry in messages:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

prompt = st.chat_input("Ask MedPredict AI a question…", max_chars=MAX_USER_CHARS)
if prompt and prompt.strip():
    prompt = prompt.strip()
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Asking Gemini 3.8 Flash…"):
            try:
                reply = generate_reply(bounded_history(messages), api_key=key, model=model)
            except Exception as err:
                st.error(friendly_error(err))
                st.caption("Your message was not saved as a completed AI exchange. Retry after resolving the issue.")

                messages.pop()
            else:
                st.markdown(reply)
                messages.append({"role": "assistant", "content": reply})

st.divider()
st.caption(
    "Chat history is kept only in this Streamlit session and is not written into MedPredict's SQLite database. "
    "It may disappear if you reload or restart the app. This assistant doesn't automatically read your uploaded scans or profile."
)
