"""Searchable, offline-first MedlinePlus condition library."""
from html import escape
import streamlit as st
from condition_library import counts, library, normalize, related_tool, search_topics
from sidebar_compat import show_sidebar
from ui import apply_theme, html

st.set_page_config(page_title="Disease Atlas | MedPredict", page_icon="📚", layout="wide")
show_sidebar()
apply_theme()
if not st.session_state.get("is_logged_in", False):
    st.warning("Sign in to explore the condition library.")
    st.page_link("app.py", label="Go to sign in")
    st.stop()

total, common = counts()
html(f'<div class="mp-library-stats"><span><b>{common}</b> common conditions</span>'
     f'<span><b>{total:,}</b> health topics</span><span>Source-linked · Available offline</span></div>')
st.caption("Source: MedlinePlus.gov, U.S. National Library of Medicine. Condition guides are educational information; they are not trained prediction models. MedPredict is not endorsed by NLM.")
with st.form("atlas_search"):
    query = st.text_input("Search for a disease or condition", value=st.session_state.get("mp_atlas_query", ""),
                          placeholder="Try epilepsy, asthma, dengue or migraine", max_chars=100)
    submitted = st.form_submit_button("Search conditions", type="primary")
if submitted:
    st.session_state["mp_atlas_query"] = query.strip()
term = st.session_state.get("mp_atlas_query", "")
left, right = st.columns([2, 1])
with left:
    groups = sorted({group for topic in library()["topics"] for group in topic["groups"]})
    group = st.selectbox("Browse by body system or topic", ["All topics"] + groups, key="atlas_group")
with right:
    scope = st.selectbox("Library view", ["Common conditions", "All health topics"], key="atlas_scope")
results = search_topics(term, common_only=not term and scope == "Common conditions",
                        group=None if group == "All topics" else group, limit=total)
signature = (term, group, scope)
if st.session_state.get("_atlas_filter") != signature:
    st.session_state["_atlas_filter"] = signature
    st.session_state.pop("atlas_topic_picker", None)
    if term and results and normalize(term) in [normalize(results[0]["title"])] + [normalize(x) for x in results[0]["aliases"]]:
        st.session_state["atlas_topic_picker"] = results[0]["id"]
if "atlas_requested_id" in st.session_state:
    requested = st.session_state.pop("atlas_requested_id")
    if any(topic["id"] == requested for topic in results):
        st.session_state["atlas_topic_picker"] = requested
if not results:
    st.info("No local topic matched. Try a shorter name, or choose All topics above.")
    st.link_button("Search MedlinePlus", "https://medlineplus.gov/healthtopics.html")
    st.stop()
st.caption(f"{len(results):,} matching topics")
lookup = {topic["id"]: topic for topic in results}
selected = st.selectbox("Select a condition", list(lookup), format_func=lambda key: lookup[key]["title"],
                        index=None, placeholder="Choose a condition or search the list…", key="atlas_topic_picker")
if selected is None:
    for offset in range(0, min(len(results), 12), 3):
        for column, topic in zip(st.columns(3), results[offset:offset + 3]):
            with column:
                with st.container(border=True, key=f"library_topic_{topic['id']}"):
                    html(f'<div class="mp-library-card"><span>{escape(topic["groups"][0] if topic["groups"] else "HEALTH TOPIC")}</span>'
                         f'<h3>{escape(topic["title"])}</h3><p>{escape(topic["description"][:180])}</p></div>')
                    if st.button("Explore condition →", key=f"atlas_open_{topic['id']}", use_container_width=True):
                        st.session_state["atlas_requested_id"] = topic["id"]
                        st.rerun()
    st.caption("Use the searchable condition list above to browse every topic in this view.")
    st.stop()
topic = lookup[selected]
html(f'<div class="mp-condition-title"><span>CONDITION GUIDE</span><h2>{escape(topic["title"])}</h2></div>')
if topic["aliases"]:
    st.caption("Also called: " + ", ".join(topic["aliases"][:6]))
overview, symptoms, care = st.tabs(["Overview", "Symptoms & tests", "Care & prevention"])
with overview:
    st.markdown(topic["summary"] or topic["description"], _mp_raw=True)
    st.link_button("Read the MedlinePlus topic ↗", topic["url"])
for panel, section in [(symptoms, "Symptoms and tests"), (care, "Care and prevention")]:
    with panel:
        links = [item for item in topic["links"] if item["section"] == section]
        if not links:
            st.write("The main source article contains the available information for this topic.")
            st.link_button("Open source article ↗", topic["url"])
        for item in links:
            with st.container(border=True):
                st.markdown(f'**{item["title"]}**', _mp_raw=True)
                st.caption(item["organization"])
                st.link_button("Read guidance ↗", item["url"])
tool = related_tool(topic)
if tool:
    with st.container(border=True, key="library_related_tool"):
        st.subheader("Related tool in MedPredict")
        if st.button(tool["label"], type="primary", key="atlas_related_tool"):
            if tool.get("screening"):
                st.session_state["mp_screening_requested"] = tool["screening"]
            st.switch_page(tool["page"])
if st.button("Ask the assistant about this condition", key="atlas_ask_assistant"):
    st.session_state["assistant_seed"] = f"Explain {topic['title']} in simple terms."
    st.switch_page("pages/8_gemini_chatbot.py")
st.caption("Information: MedlinePlus.gov, U.S. National Library of Medicine. Educational information, not an individual diagnosis or treatment plan. MedPredict is not endorsed by NLM.")
