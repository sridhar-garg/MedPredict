import streamlit as st






st.set_page_config(
    page_title="MedPredict | Health Research",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)





import streamlit.components.v1 as components
from pathlib import Path
from utils import apply_custom_css
from login import login_page
from auth import verify_family_email_token
from database import initialize_database, process_family_email_action

def render_html(html_code):
    cleaned_html = "\n".join(
        line.lstrip() for line in html_code.splitlines()
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
            "You can now log in to HealthGuard AI and open Family Health."
        )
    else:
        st.warning(_msg)

    st.stop()






if not st.session_state.get("is_logged_in", False):
    login_page()
    st.stop()






if "healthai_theme" not in st.session_state:
    st.session_state.healthai_theme = "dark"

apply_custom_css()

from sidebar_compat import show_sidebar
show_sidebar()







theme_marker = (
    "healthai-theme-dark-marker"
    if st.session_state.healthai_theme == "dark"
    else "healthai-theme-light-marker"
)

st.markdown(
    f'<div class="{theme_marker}" aria-hidden="true"></div>',
    unsafe_allow_html=True,
)






left, search_col = st.columns(
    [4.8, 3.2],
    vertical_alignment="center",
)

with left:
    render_html("""
            <div class="healthai-native-chips">
                <span class="healthai-chip active">✳ <b>MEDPREDICT STUDIO</b></span>

                <span class="healthai-chip">
                    Explainable predictions
                </span>

                <span class="healthai-chip">
                    Research tools
                </span>
            </div>
            """)


with search_col:
    with st.form("healthai_search_form", clear_on_submit=False):
        q_col, b_col = st.columns(
            [5, 1],
            vertical_alignment="center",
        )

        with q_col:
            search_query = st.text_input(
                "Disease search",
                placeholder="Find a screening or tool…",
                label_visibility="collapsed",
                key="healthai_search",
            )

        with b_col:
            submitted = st.form_submit_button(
                "⌕",
                use_container_width=True,
            )


if submitted and search_query.strip():
    q = search_query.strip().lower()

    if any(
        word in q
        for word in ["breast", "cancer", "tumor", "tumour"]
    ):
        st.switch_page("pages/breast_app.py")

    elif any(
        word in q
        for word in ["diabetes", "diabetic", "sugar"]
    ):
        st.switch_page("pages/diabetes_app.py")

    elif any(
        word in q
        for word in ["heart", "cardiac", "cardiovascular"]
    ):
        st.switch_page("pages/heart_app.py")


    elif any(k in q for k in ["hypertension", "blood pressure", "kidney", "anaemia", "anemia",
                              "cholesterol", "ldl", "obesity", "apnoea", "apnea", "liver fibrosis"]):
        st.switch_page("pages/4_health_screenings.py")

    elif any(k in q for k in ["x-ray", "xray", "fracture", "ct scan", "mri", "ultrasound",
                              "skin lesion", "imaging", "scan", "health report"]):
        st.switch_page("pages/5_medical_imaging.py")

    else:
        st.warning(
            "I couldn't find that disease. "
            "Try Diabetes, Heart Disease, or Breast Cancer."
        )


# Theme selection is globally available from the navigation sidebar.

PAGE_CSS = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
DESIGN_CSS = (Path(__file__).parent / "design_system.css").read_text(encoding="utf-8")

dark = st.session_state.healthai_theme == "dark"
iframe_theme = "dark" if dark else "light"


hero_html = f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">

    <style>
        {PAGE_CSS}
        {DESIGN_CSS}

        :root {{
            color-scheme: {iframe_theme};
        }}

        html,
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
        }}
    </style>
</head>

<body class="hero-iframe-body {iframe_theme}">

    <div
        class="{theme_marker}"
        aria-hidden="true"
        style="display:none"
    ></div>

    <section class="healthai-hero">

        <div class="healthai-hero-copy">

            <div class="healthai-eyebrow">
                <span>✦</span> THE FUTURE OF ACCESSIBLE HEALTH RESEARCH
            </div>

            <h1>
                Health insights.<br>
                <span>Reimagined.</span>
            </h1>

            <p class="healthai-lead">
                An intelligent workspace for understanding health data.
                Explore interactive screening models, explainable
                insights, and research tools in one beautiful place.
            </p>

            <div class="healthai-actions">

                <a
                    href="#assessment-section"
                    target="_top"
                    class="healthai-btn primary"
                >
                    Explore assessments&nbsp; ↗
                </a>

                <a
                    href="#models"
                    target="_top"
                    class="healthai-btn secondary"
                >
                    Explore the science
                </a>

            </div>

            <div class="healthai-mini-note">
                <span>✓</span>
                Research prototype&nbsp;&nbsp; / &nbsp;&nbsp; For education only&nbsp;&nbsp; / &nbsp;&nbsp; Not medical advice
            </div>

        </div>


        <div class="healthai-hero-art">
            <div class="mp-floating-pill top">✦ &nbsp; THE RESEARCH WORKSPACE</div>
            <div class="mp-diagnostic-graphic">
                <div class="mp-graphic-bar">
                    <span>MEDPREDICT / EXPLORER</span>
                    <span>◉ &nbsp; DEMO VIEW</span>
                </div>
                <div class="mp-signal">
                    <svg viewBox="0 0 460 275" xmlns="http://www.w3.org/2000/svg" role="img"
                         aria-label="Illustrative medical data visualization. Not actual patient measurements.">
                        <defs>
                          <radialGradient id="mp-orb" cx="50%" cy="50%" r="50%">
                            <stop offset="0" stop-color="#56f0d8" stop-opacity=".36"/>
                            <stop offset="1" stop-color="#1e9b96" stop-opacity="0"/>
                          </radialGradient>
                          <linearGradient id="mp-line" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0" stop-color="#4dd3c7"/>
                            <stop offset=".55" stop-color="#7be4d2"/>
                            <stop offset="1" stop-color="#9bb6ff"/>
                          </linearGradient>
                        </defs>
                        <circle cx="230" cy="137" r="133" fill="url(#mp-orb)"/>
                        <g fill="none" stroke="#568294" stroke-opacity=".22">
                          <circle cx="230" cy="137" r="56"/>
                          <circle cx="230" cy="137" r="90"/>
                          <circle cx="230" cy="137" r="122" stroke-dasharray="4 7"/>
                          <path d="M0 68 H460 M0 137 H460 M0 205 H460 M115 0 V275 M230 0 V275 M345 0 V275"/>
                        </g>
                        <g fill="none" stroke="#66e1ce" stroke-opacity=".65" stroke-width="1.6">
                          <path d="M230 61 C182 28 128 80 146 137 C156 173 204 208 230 230 C256 208 304 173 314 137 C332 80 278 28 230 61Z"/>
                          <path d="M230 79 C193 56 160 92 169 133 C180 161 213 186 230 202 C250 187 280 159 291 133 C302 92 265 53 230 79Z"/>
                        </g>
                        <path d="M26 146 H116 L130 142 L141 153 L159 112 L175 180 L190 145 H210 L229 126 L250 158 L271 90 L289 197 L307 146 H343 L357 137 L370 147 H435"
                          stroke="url(#mp-line)" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round" fill="none"/>
                        <circle cx="271" cy="90" r="7" fill="#66e1ce" stroke="#0d2330" stroke-width="3"/>
                        <g fill="#74d9cd"><circle cx="95" cy="44" r="3"/><circle cx="372" cy="65" r="3"/><circle cx="386" cy="210" r="3"/></g>
                        <text x="30" y="32" fill="#99b8c9" font-family="Arial" font-size="10" letter-spacing="2">SIGNAL EXPLORATION</text>
                        <text x="31" y="250" fill="#8ba9bb" font-family="Arial" font-size="10">Visual representation · no patient data</text>
                    </svg>
                </div>
                <div class="mp-graphic-foot">
                    <div class="mp-diagnostic-tile"><strong>HEART HEALTH</strong><small>Explore screening ↗</small></div>
                    <div class="mp-diagnostic-tile"><strong>DIABETES</strong><small>Explore screening ↗</small></div>
                    <div class="mp-diagnostic-tile"><strong>BREAST HEALTH</strong><small>Explore screening ↗</small></div>
                </div>
            </div>
            <div class="mp-floating-pill bottom">◇ &nbsp; EXPLAINABLE BY DESIGN</div>
        </div>

    </section>

</body>
</html>
"""


components.html(
    hero_html,
    height=660,
    scrolling=False,
)






render_html("""
        <div class="healthai-stat-grid">

            <div class="healthai-stat-card">
                <div class="stat-symbol cyan">♧</div>

                <div>
                    <strong>03</strong>
                    <span>Health Assessments</span>
                    <small>Breast • Diabetes • Heart</small>
                </div>
            </div>


            <div class="healthai-stat-card">
                <div class="stat-symbol blue">▱</div>

                <div>
                    <strong>05</strong>
                    <span>ML Models</span>
                    <small>Ensemble Approach</small>
                </div>
            </div>


            <div class="healthai-stat-card">
                <div class="stat-symbol purple">◉</div>

                <div>
                    <strong>XAI</strong>
                    <span>Explainable AI</span>
                    <small>SHAP &amp; Feature Importance</small>
                </div>
            </div>


            <div class="healthai-stat-card">
                <div class="stat-symbol teal">▥</div>

                <div>
                    <strong>Interactive</strong>
                    <span>Visual Learning</span>
                    <small>Visual Explanations</small>
                </div>
            </div>

        </div>


        <div id="models" class="healthai-section-grid">

            <section class="healthai-panel models-panel">

                <div class="panel-heading">
                    <span class="panel-icon">⚙</span>

                    <div>
                        <h3>AI Models Used</h3>

                        <p>
                            Five trained models work together to estimate risk.
                        </p>
                    </div>
                </div>


                <div class="model-list">

                    <div class="model-item">
                        <span>⌁</span>
                        <b>Logistic<br>Regression</b>
                    </div>

                    <div class="model-item">
                        <span>╱</span>
                        <b>SVM</b>
                    </div>

                    <div class="model-item">
                        <span>♧</span>
                        <b>KNN</b>
                    </div>

                    <div class="model-item">
                        <span>✣</span>
                        <b>Random<br>Forest</b>
                    </div>

                    <div class="model-item">
                        <span>𝕏</span>
                        <b>XGBoost</b>
                    </div>

                </div>

            </section>


            <section class="healthai-panel explain-panel">

                <div class="panel-heading">
                    <span class="panel-icon purple-bg">◉</span>

                    <div>
                        <h3>Why Explainability?</h3>

                        <p>
                            See which inputs influence a prediction.
                        </p>
                    </div>
                </div>


                <div class="explain-content">

                    <div class="explain-copy">
                        <b>Transparent predictions</b>

                        <span>
                            Feature importance and SHAP make model behaviour
                            easier to inspect and explain.
                        </span>
                    </div>


                    <div class="feature-bars">

                        <div>
                            <label>Age</label>
                            <i style="width:88%"></i>
                        </div>

                        <div>
                            <label>BMI</label>
                            <i style="width:70%"></i>
                        </div>

                        <div>
                            <label>Glucose</label>
                            <i style="width:55%"></i>
                        </div>

                        <div>
                            <label>Blood Pressure</label>
                            <i style="width:43%"></i>
                        </div>

                        <div>
                            <label>Cholesterol</label>
                            <i style="width:32%"></i>
                        </div>

                    </div>

                </div>

            </section>


            <section class="healthai-panel prediction-panel">

                <div class="panel-heading">
                    <span class="panel-icon teal-bg">◈</span>

                    <div>
                        <h3>Sample Prediction</h3>
                        <p>Example risk result.</p>
                    </div>
                </div>


                <div class="sample-risk">

                    <div class="risk-ring">
                        <span>12%</span>
                        <small>risk</small>
                    </div>


                    <div>
                        <span class="low-pill">✓ Low Risk</span>
                        <strong>12%</strong>
                        <small>Risk Probability</small>

                        <div class="risk-line">
                            <i></i>
                        </div>
                    </div>

                </div>

            </section>

        </div>


        <section class="healthai-workflow">

            <div class="workflow-title">
                <span>⚙</span>

                <div>
                    <h2>How HealthAI Works</h2>

                    <p>
                        From patient information to an interpretable AI result.
                    </p>
                </div>
            </div>


            <div class="workflow-steps">

                <div class="workflow-step">
                    <span>01</span>

                    <div>
                        <b>Enter Information</b>

                        <p>
                            Provide health details through the assessment form.
                        </p>
                    </div>
                </div>


                <em>→</em>


                <div class="workflow-step">
                    <span>02</span>

                    <div>
                        <b>AI Models Analyze</b>

                        <p>
                            Multiple trained models calculate risk probability.
                        </p>
                    </div>
                </div>


                <em>→</em>


                <div class="workflow-step">
                    <span>03</span>

                    <div>
                        <b>Compare Results</b>

                        <p>
                            Review model predictions and the ensemble result.
                        </p>
                    </div>
                </div>


                <em>→</em>


                <div class="workflow-step">
                    <span>04</span>

                    <div>
                        <b>Understand with XAI</b>

                        <p>
                            Inspect feature importance and SHAP explanations.
                        </p>
                    </div>
                </div>

            </div>

        </section>


        <div class="healthai-footer-note">
            <span>♥</span>
            HealthAI &nbsp;•&nbsp;
            Research / Academic Prototype &nbsp;•&nbsp;
            AI Health Risk Assessment
        </div>
        """)






st.markdown(
    '<div id="assessment" class="healthai-parent-anchor"></div>',
    unsafe_allow_html=True,
)


render_html("""
        <div id="assessment-section" class="section-heading">

            <span class="section-number">01</span>

            <div>
                <h2>Choose your assessment</h2>

                <p>
                    Select a health condition to begin the AI-based
                    risk assessment.
                </p>
            </div>

        </div>


        <p class="assessment-intro">
            Choose one of the available assessments to continue.
        </p>
        """)


card1, card2, card3 = st.columns(3)






with card1:
    render_html("""
            <div class="disease-card">

                <div class="disease-icon">🩸</div>

                <div class="disease-card-title">
                    Diabetes
                </div>

                <div class="disease-card-text">
                    Assess diabetes-related risk using patient symptoms
                    and health information.
                </div>

            </div>
            """)

    if st.button(
        "Assess Diabetes →",
        key="open_diabetes",
        use_container_width=True,
    ):
        st.switch_page("pages/diabetes_app.py")






with card2:
    render_html("""
            <div class="disease-card">

                <div class="disease-icon">❤️</div>

                <div class="disease-card-title">
                    Heart Disease
                </div>

                <div class="disease-card-text">
                    Assess cardiovascular risk from clinical measurements
                    and symptoms.
                </div>

            </div>
            """)

    if st.button(
        "Assess Heart Disease →",
        key="open_heart",
        use_container_width=True,
    ):
        st.switch_page("pages/heart_app.py")






with card3:
    render_html("""
            <div class="disease-card">

                <div class="disease-icon">🎗️</div>

                <div class="disease-card-title">
                    Breast Cancer
                </div>

                <div class="disease-card-text">
                    Assess risk from diagnostic tumor measurement features
                    and predict risks.
                </div>

            </div>
            """)

    if st.button(
        "Assess Breast Cancer →",
        key="open_breast",
        use_container_width=True,
    ):
        st.switch_page("pages/breast_app.py")






st.markdown('<div class="mp-section-kicker">EXPLORE THE PLATFORM</div>', unsafe_allow_html=True)
st.markdown("### Expand your capabilities")
more_col_1, more_col_2 = st.columns(2)
with more_col_1:
    if st.button("🩺 Explore 7 more health screenings →", key="open_addon_screenings", use_container_width=True):
        st.switch_page("pages/4_health_screenings.py")
with more_col_2:
    if st.button("🔬 Medical imaging & reports →", key="open_addon_imaging", use_container_width=True):
        st.switch_page("pages/5_medical_imaging.py")
st.caption("Extra screenings are formula-based educational tools. Imaging models are experimental and not for diagnosis.")









st.markdown("### Discover & connect")
mp_ax_col1, mp_ax_col2=st.columns(2)
with mp_ax_col1:
    if st.button('🤟 AbilityBridge — ASL, ISL & Braille',key='mp_ax_open_ability',use_container_width=True):
        st.switch_page('pages/9_abilitybridge.py')
with mp_ax_col2:
    if st.button('📚 Disease Atlas — Search conditions',key='mp_ax_open_atlas',use_container_width=True):
        st.switch_page('pages/10_disease_atlas.py')
st.caption('Accessibility and medically sourced educational information. No new unrelated labs added.')




st.markdown("### Advanced research")
st.write("Optional AI validation and autonomous robotics experiments, organised together.")
if st.button("🧪 Open Advanced Research Mode →",key="mp_open_advanced_research",use_container_width=True):
    st.switch_page("pages/11_advanced_research_mode.py")




render_html("""
        <div class="healthai-bottom-note">
            HealthAI • EXHRA • Research / Academic Prototype •
            Not a medical diagnosis
        </div>
        """)





st.markdown("### Your AI research assistant")
st.write("Ask Gemini 3.8 Flash educational health and AI research questions, with multi-turn conversation support.")
if st.button("💬 Open Gemini Chatbot →", key="medpredict_gemini38_home", use_container_width=True):
    st.switch_page("pages/8_gemini_chatbot.py")
st.caption("Educational assistance only, not clinical diagnosis. Chat history remains in your browser session.")
