"""MedPredict overview: assessments, insights, and connected health tools."""
import streamlit as st

st.set_page_config(page_title="Dashboard | MedPredict", page_icon="assets/favicon.svg",
                   layout="wide", initial_sidebar_state="collapsed")

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

html(f'''<section class="journal-hero">
<div class="journal-hero-copy"><span class="journal-eyebrow">YOUR HEALTH, CONSIDERED</span>
<h1>A thoughtful view<br>of your health.</h1>
<p>Turn everyday health information into a clearer picture. Explore an assessment, understand the factors, and keep the next step in perspective.</p>
<a class="journal-start" href="#assessments" target="_self">Find your starting point {icon("arrow", 16)}</a>
<div class="journal-hero-note">A research &amp; education workspace. Always guided by clinical advice.</div></div>
<div class="journal-hero-photo"><img src="{studio_image()}" alt="Forest-green stethoscope beside a cream notebook on ivory linen"><span>THE MEDPREDICT JOURNAL · 04</span></div>
</section>''')
html('''<div class="journal-facts"><div><b>03</b><span>Focused AI assessments</span></div><div><b>07</b><span>Additional health screenings</span></div><div><b>SHAP</b><span>Explanations behind the estimate</span></div></div>''')

main, library = st.columns([1.65, 1], gap="large")
with main:
    html('<div id="assessments" class="journal-section"><span class="journal-eyebrow">01 / BEGIN WITH THE BASICS</span><h2>Choose your assessment.</h2><p>Start with the question that brought you here.</p></div>')
    assessments = [
        ("01", "Heart health", "Clinical measurements and cardiovascular factors.", "heart", "pages/heart_app.py", "open_heart"),
        ("02", "Diabetes", "Symptoms, health indicators and model explanations.", "drop", "pages/diabetes_app.py", "open_diabetes"),
        ("03", "Breast health", "Explore estimates from diagnostic tumour measurements.", "ribbon", "pages/breast_app.py", "open_breast"),
    ]
    for number, name, copy, glyph, page, key in assessments:
        with st.container(border=True):
            left, content, action = st.columns([.5, 3.7, 1.2], vertical_alignment="center")
            with left:
                html(f'<span class="journal-assessment-icon">{icon(glyph, 23)}</span>')
            with content:
                html(f'<div class="journal-assessment"><span>{number} / ASSESSMENT</span><h3>{name}</h3><p>{copy}</p></div>')
            with action:
                if st.button("Begin →", key=key, use_container_width=True, type="primary"):
                    st.switch_page(page)
    st.caption("Model estimates support learning. They do not confirm or exclude a diagnosis.")

with library:
    html('<div class="journal-section"><span class="journal-eyebrow">02 / EXPLORE FURTHER</span><h2>Your health library.</h2><p>A little context can make a difference.</p></div>')
    with st.container(border=True):
        for path, label, glyph in [
            ("pages/4_health_screenings.py", "More health screenings", "health_metrics"),
            ("pages/5_medical_imaging.py", "Imaging & report explorer", "radiology"),
            ("pages/10_disease_atlas.py", "Disease atlas", "menu_book"),
            ("pages/8_gemini_chatbot.py", "Ask the AI assistant", "chat_bubble_outline"),
            ("pages/history.py", "Your assessment history", "history"),
            ("pages/z_family.py", "Family health", "group"),
        ]:
            st.page_link(path, label=label, icon=f":material/{glyph}:")
    with st.container(border=True):
        html('<div class="journal-quiet-card"><span class="journal-eyebrow">YOUR EXPERIENCE MATTERS</span><h3>A space for feedback.</h3><p>See illustrative interface reviews. Verified feedback and real usage findings can be added after assessment trials.</p></div>')
        st.page_link("pages/12_reviews.py", label="Read demo reviews", icon=":material/rate_review:")

html('<div class="journal-method"><span class="journal-eyebrow">03 / FROM INFORMATION TO INSIGHT</span><h2>Simple steps. A clearer picture.</h2></div>')
for col, number, title, copy in zip(st.columns(3), ["01", "02", "03"], ["Share your information", "Explore the estimate", "Understand the factors"], ["Enter the measurements requested by your assessment.", "Compare the available models and their limitations.", "Review the explanation and discuss concerns with a clinician."]):
    with col:
        html(f'<div class="journal-step"><b>{number}</b><h3>{title}</h3><p>{copy}</p></div>')
html('<div class="journal-footer"><span>MedPredict · A considered approach to health.</span><span>Research &amp; education · Not a medical diagnosis</span></div>')
