"""MedPredict overview: assessments, insights, and connected health tools."""
import streamlit as st

st.set_page_config(page_title="MedPredict | Your health workspace", page_icon="assets/favicon.svg",
                   layout="wide", initial_sidebar_state="expanded")

from auth import verify_family_email_token
from database import initialize_database, process_family_email_action
from login import login_page
from sidebar_compat import show_sidebar
from ui import apply_theme, html, icon, section, studio_image, tool_card

st.session_state.setdefault("is_logged_in", False)

initialize_database()

_family_action = st.query_params.get("family_action")
_family_token = st.query_params.get("family_token")

if _family_action and _family_token:
    _verified = verify_family_email_token(_family_token)

    if _verified is None:
        st.error("This family email link is invalid or has expired.")
        st.stop()

    _connection_id, _recipient_user_id = _verified

    _ok, _msg, _requester_email = process_family_email_action(
        _connection_id,
        _recipient_user_id,
        _family_action,
    )

    if _ok:
        st.success("✓ " + _msg)
        st.info(
            "You can now log in to MedPredict and open Family Health."
        )
    else:
        st.warning(_msg)

    st.stop()


if not st.session_state.get("is_logged_in", False):
    login_page()
    st.stop()


show_sidebar()
apply_theme()

workspace_col, search_col = st.columns([4, 3], vertical_alignment="center")
with workspace_col:
    html('<div class="mp-topbar"><span class="mp-status-dot"></span> YOUR HEALTH WORKSPACE</div>')
with search_col:
    with st.form("healthai_search_form", border=False):
        field_col, submit_col = st.columns([4, 1.3], vertical_alignment="bottom")
        with field_col:
            search_query = st.text_input("Disease search", placeholder="Find a condition…",
                                         label_visibility="collapsed", key="healthai_search")
        with submit_col:
            submitted = st.form_submit_button("Search", use_container_width=True)

if submitted and search_query.strip():
    query = search_query.strip().lower()
    destinations = [
        (["breast", "cancer", "tumor", "tumour"], "pages/breast_app.py"),
        (["diabetes", "diabetic", "sugar"], "pages/diabetes_app.py"),
        (["heart", "cardiac", "cardiovascular"], "pages/heart_app.py"),
        (["hypertension", "blood pressure", "kidney", "anaemia", "anemia", "cholesterol", "ldl",
          "obesity", "apnoea", "apnea", "liver fibrosis"], "pages/4_health_screenings.py"),
        (["x-ray", "xray", "fracture", "ct scan", "mri", "ultrasound", "skin lesion", "imaging",
          "scan", "health report"], "pages/5_medical_imaging.py"),
    ]
    for terms, page in destinations:
        if any(term in query for term in terms):
            st.switch_page(page)
    st.info("Try diabetes, heart disease, breast cancer, blood pressure, or medical imaging. For other conditions, open Disease atlas in the sidebar.")

html('''<div class="mp-welcome"><h1>Your health, in focus.</h1>
<p>A little understanding today. More informed decisions tomorrow.</p></div>''')

html(f'''<section class="mp-hero" aria-label="Welcome to your health workspace">
<img class="mp-hero-art" src="{studio_image()}" alt="Stethoscope on an indigo surface">
<div class="mp-hero-copy"><span class="mp-eyebrow">{icon("spark", 14)} INSIGHT BEGINS WITH YOU</span>
<h2>Know a little more.<br><span class="mp-heading-accent">Care a little better.</span></h2>
<p>Bring your health information into focus with AI-assisted risk assessments and explanations that make sense.</p>
<a class="mp-hero-link" href="#assessments" target="_self">Explore assessments {icon("arrow", 14)}</a>
<div class="mp-hero-footnote">Educational insights. Always guided by clinical advice.</div></div></section>''')

html(f'''<div class="mp-capabilities">
<div class="mp-capability">{icon("pulse",22)}<div><b>3 focused assessments</b><small>Heart, diabetes &amp; breast health</small></div></div>
<div class="mp-capability">{icon("spark",22)}<div><b>Understand the factors</b><small>Model comparisons &amp; SHAP explanations</small></div></div>
<div class="mp-capability">{icon("history",22)}<div><b>Your progress, together</b><small>Saved assessments &amp; family health</small></div></div>
</div>''')

html('<div id="assessments"></div>')
section("Where would you like to begin?", "Choose an assessment to explore the factors behind your health.", "YOUR NEXT STEP")
c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    tool_card("Diabetes", "Explore diabetes-related risk using your symptoms and health information.",
              "drop", "pages/diabetes_app.py", "open_diabetes", "violet", "Assess diabetes")
with c2:
    tool_card("Heart health", "Understand cardiovascular risk using clinical measurements and symptoms.",
              "heart", "pages/heart_app.py", "open_heart", "rose", "Assess heart health")
with c3:
    tool_card("Breast health", "Explore model estimates from diagnostic tumour measurements.",
              "ribbon", "pages/breast_app.py", "open_breast", "blue", "Assess breast health")

section("More ways to understand your health", "Explore your information, find answers, and keep everything connected.", "BEYOND THE ASSESSMENT")
tools = [
    ("More health screenings", "Seven additional educational screenings, from blood pressure to kidney health.", "pulse", "pages/4_health_screenings.py", "open_addon_screenings", "teal", "Explore screenings"),
    ("Imaging & reports", "Explore medical images and make sense of the information in health reports.", "scan", "pages/5_medical_imaging.py", "open_addon_imaging", "blue", "Explore reports"),
    ("AI assistant", "Ask questions about health terms, medical information, and AI research.", "chat", "pages/8_gemini_chatbot.py", "medpredict_gemini38_home", "violet", "Start a conversation"),
    ("Disease atlas", "Discover conditions and learn from medically sourced educational information.", "book", "pages/10_disease_atlas.py", "mp_ax_open_atlas", "blue", "Browse the atlas"),
    ("Your assessment history", "Revisit your saved assessments and explore how your results compare.", "history", "pages/history.py", "mp_open_history", "violet", "View your history"),
    ("Family health", "Manage family connections and the health information you choose to share.", "people", "pages/z_family.py", "mp_open_family", "teal", "Open family health"),
]
for start in range(0, len(tools), 3):
    for col, tool in zip(st.columns(3, gap="medium"), tools[start:start+3]):
        with col:
            tool_card(*tool)
with st.expander("Accessibility in MedPredict"):
    st.write("Use fingerspelling recognition and text-to-Braille tools within your MedPredict workspace.")
    if st.button("Open accessibility tools →", key="mp_ax_open_ability"):
        st.switch_page("pages/9_abilitybridge.py")
st.caption("Additional screenings use educational formulas. Imaging models are experimental; neither replaces clinical assessment.")

section("A clearer path from information to insight", eyebrow="HOW IT WORKS")
steps = [
    ("01", "Share your information", "Enter the measurements requested by your chosen assessment."),
    ("02", "Explore the estimate", "Compare model outputs and understand their limitations."),
    ("03", "Understand the factors", "Review the explanations and discuss concerns with a clinician."),
]
for col, (number, title, copy) in zip(st.columns(3), steps):
    with col:
        html(f'<div class="mp-step"><span class="mp-step-number">{number}</span><div><h4>{title}</h4><p>{copy}</p></div></div>')
html('<div class="mp-footer"><span>MedPredict. A clearer perspective.</span><span>Research &amp; education · Not a medical diagnosis</span></div>')
