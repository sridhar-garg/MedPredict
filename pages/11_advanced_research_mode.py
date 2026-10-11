"""One user-friendly entry point for the two earlier research labs."""
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Advanced Research Mode | MedPredict X",page_icon="🧪",layout="wide")


from sidebar_compat import show_sidebar
show_sidebar()
try:
    from utils import apply_custom_css
    apply_custom_css()
except (ImportError,AttributeError):
    pass
if not st.session_state.get("is_logged_in",False):
    st.warning("Please sign in first.")
    st.page_link("app.py",label="Back to login",icon="🏠")
    st.stop()

st.title("🧪 Advanced Research Mode")
st.caption("Optional tools for competition demonstration, model evaluation and autonomous-robot research")
st.info("These are separate experimental projects. Results from the robot simulation are synthetic, "
        "and model evaluation does not establish clinical safety or diagnostic approval.")
left,right=st.columns(2,gap="large")
with left:
    st.subheader("🔬 AI Model Research")
    st.write("Evaluate medical AI, calibration, held-out experiments, visual explanations, "
             "robustness and documented limitations.")
    if Path('pages/6_research_hub.py').is_file():
        if st.button("Open AI Model Research",use_container_width=True,type="primary"):
            st.switch_page("pages/6_research_hub.py")
    else:
        st.warning("The previous Research Hub is not installed on this copy.")
with right:
    st.subheader("🤖 Autonomous Robotics")
    st.write("Explore CARE-BOT's simulated robot routes, obstacles, task selection "
             "and reproducible benchmark comparisons.")
    if Path('pages/7_autonomous_lab.py').is_file():
        if st.button("Open CARE-BOT Experiments",use_container_width=True):
            st.switch_page("pages/7_autonomous_lab.py")
    else:
        st.warning("The previous CARE-BOT Lab is not installed on this copy.")
st.divider()
st.caption("These labs remain available through this portal but no longer take up two "
           "separate places in your sidebar. This feature does not remove or reset either experiment.")
