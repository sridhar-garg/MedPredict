"""MedPredict conversation workspace with online and source-linked guide answers."""
from pathlib import Path
import streamlit as st
from health_assistant import MAX_USER_CHARS, answer_question, load_settings
from sidebar_compat import show_sidebar
from ui import apply_theme, html

st.set_page_config(page_title="AI Assistant | MedPredict", page_icon="💬", layout="wide", initial_sidebar_state="auto")
show_sidebar()
apply_theme()
if not st.session_state.get("is_logged_in", False):
    st.warning("Please sign in before using the assistant.")
    st.page_link("app.py", label="Return to login")
    st.stop()

key, configured_model = load_settings(Path(__file__).resolve().parents[1], st.secrets)
if st.session_state.pop("assistant_force_online", False) and key:
    st.session_state["assistant_answer_source"] = "Online AI"
mode = st.radio("Answer source", ["Online AI", "Condition guide"] if key else ["Condition guide"], horizontal=True, key="assistant_answer_source")
if mode == "Online AI":
    html('<div class="mp-assistant-state"><span class="mp-status-dot"></span>Online AI selected · Library backup available</div>')
    st.caption("Messages you send in Online AI mode are processed by Google. Keep names, contact details and identifiable health records out of the conversation.")
else:
    html('<div class="mp-assistant-state"><span class="mp-status-dot"></span>Condition guide available · Source-linked answers</div>')
    st.caption("This mode retrieves condition information from the bundled MedlinePlus library; it does not generate AI answers." + (" Online AI becomes available when the deployment is connected." if not key else ""))

account_id = st.session_state.user_id
if st.session_state.get("medpredict_gemini_account") != account_id:
    from database import get_workspace_items
    saved = get_workspace_items(account_id, "AI assistant")
    st.session_state.medpredict_gemini_account = account_id
    st.session_state.medpredict_gemini_messages = saved[0]["payload"].get("messages", []) if saved else []
messages = st.session_state.setdefault("medpredict_gemini_messages", [])
with st.container(horizontal=True):
    if st.button("New conversation", icon=":material/add_comment:", key="assistant_new"):
        messages.clear()
        st.rerun()
    st.page_link("pages/history.py", label="Saved conversations", icon=":material/history:")

if not messages:
    st.markdown("**Start with a question.**")
    prompts = ["Explain epilepsy", "What is asthma?", "How does SHAP work?"]
    for column, suggestion in zip(st.columns(3), prompts):
        with column:
            if st.button(suggestion, key="assistant_suggest_" + suggestion, use_container_width=True):
                st.session_state["assistant_pending_prompt"] = suggestion

for entry in messages:
    with st.chat_message(entry["role"]):
        if entry["role"] == "assistant":
            source = entry.get("answer_mode", "saved")
            st.caption("Online AI · " + entry.get("model", "Gemini") if source == "online" else "Condition guide · MedlinePlus / educational reference" if source == "library" else "Saved conversation")
            if entry.get("provider_unavailable"):
                st.caption(entry.get("availability_message", "Online AI could not respond.") + " The answer below comes from the condition guide.")
        st.markdown(entry.get("content", ""), _mp_raw=True)

if messages and messages[-1].get("provider_unavailable") and key:
    if st.button("Retry the online answer", key="assistant_retry"):
        messages.pop()
        last = messages.pop() if messages and messages[-1]["role"] == "user" else None
        if last:
            st.session_state["assistant_pending_prompt"] = last["content"]
            st.session_state["assistant_force_online"] = True
        st.rerun()

typed = st.chat_input("Ask a question or enter a condition name…", max_chars=MAX_USER_CHARS, key="assistant_chat_input")
prompt = typed or st.session_state.pop("assistant_seed", None) or st.session_state.pop("assistant_pending_prompt", None)
if prompt and prompt.strip():
    prompt = prompt.strip()[:MAX_USER_CHARS]
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt, _mp_raw=True)
    with st.chat_message("assistant"):
        with st.spinner("Finding an answer…"):
            answer = answer_question(messages, api_key=key, model=configured_model, use_online=mode == "Online AI")
        st.caption("Online AI · " + answer.model if answer.mode == "online" else "Condition guide · MedlinePlus / educational reference")
        if answer.provider_unavailable:
            st.caption(answer.availability_message + " Showing a condition-guide answer instead.")
        st.markdown(answer.text, _mp_raw=True)
    messages.append(dict(role="assistant", content=answer.text, answer_mode=answer.mode,
                         model=answer.model, provider_unavailable=answer.provider_unavailable,
                         availability_message=answer.availability_message))
    from workspace import save_work
    save_work("AI assistant", prompt[:80], {"messages": list(messages)})
st.caption("Answers support learning; they do not diagnose a condition. Conversations are saved to your account and can be reopened in History.")
