from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="HealthAI | EXHRA",
    page_icon=str(Path(__file__).parent / "assets" / "favicon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils import apply_custom_css
from login import login_page
from auth import verify_family_email_token
from database import initialize_database, process_family_email_action


def render_html(html_code):
    """Render an HTML block. Blank lines and indentation are removed because
    Markdown would otherwise end the HTML block or treat lines as code."""
    cleaned_html = "\n".join(
        line.strip() for line in html_code.splitlines() if line.strip()
    )
    st.markdown(cleaned_html, unsafe_allow_html=True)


if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

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
            "You can now log in to HealthAI and open Family Health."
        )
    else:
        st.warning(_msg)

    st.stop()


if not st.session_state.get("is_logged_in", False):
    login_page()
    st.stop()


if "healthai_theme" not in st.session_state:
    st.session_state.healthai_theme = "light"

apply_custom_css()

from sidebar_compat import show_sidebar
show_sidebar()

dark = st.session_state.healthai_theme == "dark"
theme_marker = (
    "healthai-theme-dark-marker" if dark else "healthai-theme-light-marker"
)

st.markdown(
    f'<div class="{theme_marker}" aria-hidden="true"></div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- top bar
left, search_col, theme_col = st.columns(
    [3.6, 3.4, 1.1],
    vertical_alignment="center",
)

with left:
    render_html("""
        <p class="hx-topnote">
        <strong>Research prototype.</strong> Not a medical diagnosis.
        </p>
    """)

with search_col:
    with st.form("healthai_search_form", clear_on_submit=False):
        q_col, b_col = st.columns([4, 1.6], vertical_alignment="center")

        with q_col:
            search_query = st.text_input(
                "Search conditions",
                placeholder="Search a condition",
                label_visibility="collapsed",
                key="healthai_search",
            )

        with b_col:
            submitted = st.form_submit_button(
                "Search",
                use_container_width=True,
            )

if submitted and search_query.strip():
    q = search_query.strip().lower()

    if any(word in q for word in ["breast", "cancer", "tumor", "tumour"]):
        st.switch_page("pages/breast_app.py")

    elif any(word in q for word in ["diabetes", "diabetic", "sugar"]):
        st.switch_page("pages/diabetes_app.py")

    elif any(word in q for word in ["heart", "cardiac", "cardiovascular"]):
        st.switch_page("pages/heart_app.py")

    elif any(k in q for k in ["hypertension", "blood pressure", "kidney", "anaemia", "anemia",
                              "cholesterol", "ldl", "obesity", "apnoea", "apnea", "liver fibrosis"]):
        st.switch_page("pages/4_health_screenings.py")

    elif any(k in q for k in ["x-ray", "xray", "fracture", "ct scan", "mri", "ultrasound",
                              "skin lesion", "imaging", "scan", "health report"]):
        st.switch_page("pages/5_medical_imaging.py")

    else:
        st.warning(
            "No match found. Try diabetes, heart disease or breast cancer."
        )

with theme_col:
    if st.button(
        "Light mode" if dark else "Dark mode",
        key="healthai_theme_toggle",
        help="Switch light / dark theme",
        use_container_width=True,
    ):
        st.session_state.healthai_theme = "light" if dark else "dark"
        st.rerun()


# ------------------------------------------------------------------- hero
render_html("""
<section class="hx-hero">
<div>
<h1>Multi-disease health risk assessment</h1>
<p class="hx-lead">Enter clinical details for diabetes, heart disease or breast cancer. Five machine-learning models estimate the risk and show which inputs drove the result.</p>
<div class="hx-actions">
<a class="hx-btn primary" href="#assessment-section">Start an assessment</a>
<a class="hx-btn" href="#how-it-works">How it works</a>
</div>
</div>
<div class="hx-report" role="img" aria-label="Example result: 12 percent risk, low. Age and BMI influenced the result most.">
<div class="hx-report-head"><b>Example result</b><span>Illustrative, not real patient data</span></div>
<div class="hx-risk"><span class="hx-risk-value">12%</span><span class="hx-risk-label">Low risk</span></div>
<div class="hx-gauge"><span class="hx-gauge-mark"></span></div>
<div class="hx-gauge-scale"><span>Low: under 30%</span><span>Moderate: 30 to 70%</span><span>High: over 70%</span></div>
<div class="hx-factors">
<p class="hx-factors-title">What influenced this result</p>
<div class="hx-factor"><span>Age</span><i style="width:88%"></i></div>
<div class="hx-factor"><span>BMI</span><i style="width:70%"></i></div>
<div class="hx-factor"><span>Glucose</span><i style="width:55%"></i></div>
<div class="hx-factor"><span>Blood pressure</span><i style="width:43%"></i></div>
<div class="hx-factor"><span>Cholesterol</span><i style="width:32%"></i></div>
</div>
<p class="hx-report-foot">Every real result shows each model's estimate and the inputs behind it.</p>
</div>
</section>
<div class="hx-facts">
<div class="hx-fact"><strong>3 assessments</strong><span>Diabetes, heart disease, breast cancer</span></div>
<div class="hx-fact"><strong>5 models</strong><span>Logistic regression, SVM, KNN, random forest, XGBoost</span></div>
<div class="hx-fact"><strong>Explained</strong><span>SHAP values and feature importance</span></div>
</div>
""")


# ------------------------------------------------------------ assessments
render_html("""
<div id="assessment-section" class="hx-section-head">
<h2>Choose an assessment</h2>
<p>Pick a condition to open its form.</p>
</div>
""")

card1, card2, card3 = st.columns(3)

with card1:
    render_html("""
    <div class="hx-card">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3s6 6.2 6 10.5a6 6 0 0 1-12 0C6 9.2 12 3 12 3z"/></svg>
    <h3>Diabetes</h3>
    <p>Assess diabetes-related risk using patient symptoms and health information.</p>
    </div>
    """)
    if st.button("Start diabetes assessment", key="open_diabetes", use_container_width=True):
        st.switch_page("pages/diabetes_app.py")

with card2:
    render_html("""
    <div class="hx-card">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>
    <h3>Heart disease</h3>
    <p>Assess cardiovascular risk from clinical measurements and symptoms.</p>
    </div>
    """)
    if st.button("Start heart disease assessment", key="open_heart", use_container_width=True):
        st.switch_page("pages/heart_app.py")

with card3:
    render_html("""
    <div class="hx-card">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c-2.8 0-4.5 2-4.5 4.2 0 3 3 5.3 4.5 7.8 1.5-2.5 4.5-4.8 4.5-7.8C16.5 5 14.8 3 12 3z"/><path d="M12 15l-4 6M12 15l4 6"/></svg>
    <h3>Breast cancer</h3>
    <p>Assess risk from diagnostic tumour measurement features.</p>
    </div>
    """)
    if st.button("Start breast cancer assessment", key="open_breast", use_container_width=True):
        st.switch_page("pages/breast_app.py")


# ------------------------------------------------------------ how it works
render_html("""
<div id="how-it-works" class="hx-section-head" style="margin-top:56px">
<h2>How it works</h2>
<p>From patient information to a result you can interpret.</p>
</div>
<div class="hx-how">
<div class="hx-step"><b><span>1</span>Enter information</b><p>Provide health details in the assessment form.</p></div>
<div class="hx-step"><b><span>2</span>Models analyse</b><p>Five trained models each estimate the risk probability.</p></div>
<div class="hx-step"><b><span>3</span>Compare</b><p>Review each model's estimate and the combined result.</p></div>
<div class="hx-step"><b><span>4</span>Understand</b><p>Inspect feature importance and SHAP explanations.</p></div>
</div>
<div class="hx-method">
<div><h3>Five models, one estimate</h3><p>Logistic regression, SVM, KNN, random forest and XGBoost each produce a probability. The overall estimate is the average of the available models.</p></div>
<div><h3>Explanations you can check</h3><p>Feature importance and SHAP show which inputs pushed a result up or down, so you can see why the models gave their estimate.</p></div>
</div>
""")


# --------------------------------------------------------------- more tools
render_html("""
<div class="hx-section-head"><h2>More tools</h2></div>
""")

more_col_1, more_col_2 = st.columns(2)
with more_col_1:
    if st.button("Health screenings (7 more)", key="open_addon_screenings", use_container_width=True):
        st.switch_page("pages/4_health_screenings.py")
    if st.button("AbilityBridge: ASL, ISL and Braille", key="mp_ax_open_ability", use_container_width=True):
        st.switch_page("pages/9_abilitybridge.py")
with more_col_2:
    if st.button("Medical imaging and reports", key="open_addon_imaging", use_container_width=True):
        st.switch_page("pages/5_medical_imaging.py")
    if st.button("Disease Atlas: search conditions", key="mp_ax_open_atlas", use_container_width=True):
        st.switch_page("pages/10_disease_atlas.py")

st.caption(
    "Extra screenings are formula-based educational tools. Imaging models are "
    "experimental and not for diagnosis. AbilityBridge and Disease Atlas are "
    "accessibility and educational resources."
)


# ------------------------------------------------------------- AI assistant
render_html("""
<div class="hx-section-head" style="margin-top:40px">
<h2>MedPredict AI assistant</h2>
<p>Ask Gemini 3.8 Flash educational health and AI research questions, with multi-turn conversation support.</p>
</div>
""")

if st.button("Open assistant", key="medpredict_gemini38_home", use_container_width=True):
    st.switch_page("pages/8_gemini_chatbot.py")

st.caption(
    "Educational assistance only, not clinical diagnosis. "
    "Chat history remains in your browser session."
)

render_html("""
<p class="hx-disclaimer">HealthAI (EXHRA) is a research and academic prototype. Results are not a medical diagnosis.</p>
""")
