"""Shared native navigation for MedPredict's existing Streamlit pages."""
from inspect import currentframe
from pathlib import Path

import streamlit as st
from ui import brand, html, theme_switch


_NAV_GROUPS = [
    ("WORKSPACE", [
        ("app.py", "Overview", "space_dashboard"),
        ("pages/history.py", "Assessment history", "history"),
    ]),
    ("ASSESSMENTS", [
        ("pages/diabetes_app.py", "Diabetes", "water_drop"),
        ("pages/heart_app.py", "Heart health", "favorite"),
        ("pages/breast_app.py", "Breast health", "health_and_safety"),
        ("pages/4_health_screenings.py", "More screenings", "health_metrics"),
    ]),
    ("EXPLORE", [
        ("pages/5_medical_imaging.py", "Imaging & reports", "radiology"),
        ("pages/8_gemini_chatbot.py", "AI assistant", "chat_bubble_outline"),
        ("pages/10_disease_atlas.py", "Disease atlas", "menu_book"),
        ("pages/9_abilitybridge.py", "Accessibility tools", "accessibility_new"),
    ]),
    ("YOUR ACCOUNT", [
        ("pages/z_family.py", "Family health", "group"),
        ("pages/profile.py", "My profile", "person_outline"),
    ]),
]


def show_sidebar(current_page=None):
    if current_page is None:
        frame = currentframe()
        current_page = frame.f_back.f_code.co_filename
        del frame
    current_path = Path(current_page).resolve()
    root = Path(__file__).resolve().parent

    with st.sidebar:
        html('<div class="mp-sidebar-brand">' + brand() +
             '<div class="mp-side-caption">A clearer perspective</div></div>')
        for index, (heading, links) in enumerate(_NAV_GROUPS):
            with st.container(key=f"mp_nav_group_{index}"):
                html(f'<div class="mp-nav-label">{heading}</div>')
                for path, label, glyph in links:
                    is_current = (root / path).resolve() == current_path
                    container_key = "mp_nav_current" if is_current else f"mp_nav_{Path(path).stem}"
                    with st.container(key=container_key):
                        st.page_link(path, label=label, icon=f":material/{glyph}:")
        with st.container(key="mp_sidebar_footer"):
            theme_switch()
            html('<div class="mp-sidebar-note">Educational prototype<br>'
                 '<span>Not a medical diagnosis.</span></div>')
