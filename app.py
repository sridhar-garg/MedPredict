import streamlit as st






st.set_page_config(
    page_title="MedPredict | Health Research",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)





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
            "You can now log in to MedPredict and open Family Health."
        )
    else:
        st.warning(_msg)

    st.stop()






if not st.session_state.get("is_logged_in", False):
    login_page()
    st.stop()






# All business and account workflows above remain unchanged.
# Everything below is a new, native Streamlit workspace.
st.session_state.setdefault("healthai_theme", "dark")
apply_custom_css()


def _navigate(destination: str):
    st.switch_page(destination)


def _tool_card(title: str, description: str, icon: str, path: str, key: str):
    """Clickable, accessible launch tile. No fake HTML buttons or iframe links."""
    with st.container(border=True):
        st.markdown(
            f'<div class="mp-tool-icon" aria-hidden="true">{icon}</div>'
            f'<div class="mp-tool-name">{title}</div>'
            f'<p class="mp-tool-desc">{description}</p>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Open workspace  ↗",
            key=key,
            use_container_width=True,
            type="secondary",
        ):
            _navigate(path)


def _tool_row(items):
    cols = st.columns(len(items), gap="medium")
    for col, item in zip(cols, items):
        with col:
            _tool_card(*item)


st.markdown(
    '<div class="mp-dashboard-breadcrumb">'
    '<span class="mp-status-dot"></span> MEDPREDICT / WORKSPACE'
    '<span class="mp-dash-version">RESEARCH EDITION</span>'
    '</div>',
    unsafe_allow_html=True,
)

intro, companion = st.columns([1.9, 1], gap="large", vertical_alignment="top")
with intro:
    st.markdown(
        '<div class="mp-dashboard-intro">'
        '<div class="mp-eyebrow">YOUR HEALTH RESEARCH, ORGANIZED</div>'
        '<h1>What would you like<br>to <em>explore today?</em></h1>'
        '<p>Choose a health screening, understand your results, or go deeper '
        'into the research behind intelligent medical tools.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    start, secondary = st.columns([1.05, 1], gap="small")
    with start:
        if st.button(
            "Start heart assessment  ↗",
            key="mp_dashboard_start",
            type="primary",
            use_container_width=True,
        ):
            _navigate("pages/heart_app.py")
    with secondary:
        if st.button(
            "Open disease atlas",
            key="mp_dashboard_atlas",
            use_container_width=True,
        ):
            _navigate("pages/10_disease_atlas.py")

with companion:
    with st.container(border=True):
        st.markdown(
            '<div class="mp-spotlight">'
            '<div class="mp-spotlight-top">YOUR RESEARCH TOOLKIT <span>✳</span></div>'
            '<div class="mp-spotlight-count">03 <span>core screenings</span></div>'
            '<div class="mp-spotlight-rule"></div>'
            '<p>Explore heart disease, diabetes, and breast-health'
            ' models, plus additional educational tools.</p>'
            '<div class="mp-spotlight-tag">◉ &nbsp; Transparent, educational models</div>'
            '</div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="mp-search-heading">FIND A TOOL</div>', unsafe_allow_html=True)
with st.form("mp_tool_search_form", clear_on_submit=False, border=False):
    search_col, go_col = st.columns([5, .9], vertical_alignment="bottom", gap="small")
    with search_col:
        query = st.text_input(
            "Search by condition or tool",
            placeholder="Try heart, diabetes, imaging, kidney, research...",
            key="mp_new_search_query",
            label_visibility="collapsed",
        )
    with go_col:
        search_go = st.form_submit_button(
            "Search",
            type="primary",
            use_container_width=True,
        )

if search_go and query.strip():
    q = query.strip().lower()
    routes = [
        (["breast", "cancer", "tumor", "tumour"], "pages/breast_app.py"),
        (["diabetes", "diabetic", "sugar"], "pages/diabetes_app.py"),
        (["heart", "cardiac", "cardiovascular"], "pages/heart_app.py"),
        (["hypertension", "blood pressure", "kidney", "anaemia", "anemia",
          "cholesterol", "ldl", "obesity", "apnoea", "apnea", "liver", "screening"],
         "pages/4_health_screenings.py"),
        (["x-ray", "xray", "fracture", "ct", "mri", "ultrasound", "imaging", "scan",
          "report"], "pages/5_medical_imaging.py"),
        (["atlas", "disease information", "condition"], "pages/10_disease_atlas.py"),
        (["assistant", "chatbot", "gemini"], "pages/8_gemini_chatbot.py"),
        (["braille", "sign language", "accessibility"], "pages/9_abilitybridge.py"),
        (["research", "model validation", "experiment"], "pages/11_advanced_research_mode.py"),
    ]
    matched = next(
        (destination for keywords, destination in routes
         if any(word in q for word in keywords)),
        None,
    )
    if matched:
        _navigate(matched)
    else:
        st.info("No matching tool found. Try a condition name or select one of the workspaces below.")

st.markdown(
    '<div class="mp-workspace-title">'
    '<div><span>01 / SELECT A WORKSPACE</span>'
    '<h2>Your toolkit</h2></div>'
    '<p>Purpose-built tools, grouped by what you want to do.</p>'
    '</div>',
    unsafe_allow_html=True,
)

screenings, explore, research, account = st.tabs([
    "Health screenings",
    "Learning & AI",
    "Research lab",
    "My workspace",
])

with screenings:
    st.markdown(
        '<div class="mp-tab-description">START HERE / HEALTH ASSESSMENTS</div>',
        unsafe_allow_html=True,
    )
    _tool_row([
        ("Heart health", "Explore cardiovascular measurements and model-based estimates.",
         "♡", "pages/heart_app.py", "mp_tool_heart"),
        ("Diabetes", "Understand patterns from reported clinical and symptom inputs.",
         "◇", "pages/diabetes_app.py", "mp_tool_diabetes"),
        ("Breast health", "Explore a diagnostic-feature research model with clear explanations.",
         "✳", "pages/breast_app.py", "mp_tool_breast"),
    ])
    _tool_row([
        ("Additional screenings", "Seven educational screening and classification tools.",
         "⊕", "pages/4_health_screenings.py", "mp_tool_more"),
        ("Imaging & reports", "Explore de-identified medical images and report workflows.",
         "⌗", "pages/5_medical_imaging.py", "mp_tool_imaging"),
    ])

with explore:
    st.markdown(
        '<div class="mp-tab-description">EXPLORE / LEARN AND CONNECT</div>',
        unsafe_allow_html=True,
    )
    _tool_row([
        ("Disease atlas", "Research condition summaries and medical reference links.",
         "▤", "pages/10_disease_atlas.py", "mp_tool_atlas"),
        ("AI assistant", "Ask educational questions about health and AI research.",
         "✦", "pages/8_gemini_chatbot.py", "mp_tool_chat"),
        ("Accessibility", "Explore sign-language and Braille learning tools.",
         "⠿", "pages/9_abilitybridge.py", "mp_tool_access"),
    ])

with research:
    st.markdown(
        '<div class="mp-tab-description">ADVANCED / EXPERIMENT AND EVALUATE</div>',
        unsafe_allow_html=True,
    )
    _tool_row([
        ("Advanced research", "Your entry point for experimental research projects.",
         "✧", "pages/11_advanced_research_mode.py", "mp_tool_adv"),
        ("Model evaluation", "Investigate validation, explainability and quality.",
         "◉", "pages/6_research_hub.py", "mp_tool_lab"),
        ("CARE-BOT lab", "Explore transparent synthetic robotics simulations.",
         "⌘", "pages/7_autonomous_lab.py", "mp_tool_robot"),
    ])

with account:
    st.markdown(
        '<div class="mp-tab-description">PERSONAL / YOUR ACCOUNT</div>',
        unsafe_allow_html=True,
    )
    _tool_row([
        ("Assessment history", "Review stored results and evaluation summaries.",
         "◷", "pages/history.py", "mp_tool_history"),
        ("Profile & settings", "View and update your account information.",
         "◎", "pages/profile.py", "mp_tool_profile"),
        ("Family connections", "Manage consent-based family connections.",
         "◇", "pages/z_family.py", "mp_tool_family"),
    ])

st.markdown(
    '<div class="mp-dashboard-footer">'
    '<span>✳ &nbsp; MEDPREDICT</span>'
    '<p>Research and educational use only. Machine-learning outputs are not'
    ' medical diagnoses and must not replace professional clinical advice.</p>'
    '</div>',
    unsafe_allow_html=True,
)
