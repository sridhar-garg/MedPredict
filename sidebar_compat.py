"""Shared native navigation for MedPredict's existing Streamlit pages."""
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


def show_sidebar():
    with st.sidebar:
        html(brand() + '<div class="mp-side-caption">A clearer perspective</div>')
        for heading, links in _NAV_GROUPS:
            html(f'<div class="mp-nav-label">{heading}</div>')
            for path, label, glyph in links:
                st.page_link(path, label=label, icon=f":material/{glyph}:")
        theme_switch()
        html('<div class="mp-sidebar-note"><b>Built for understanding.</b>'
             'Research and education only.<br>Always discuss health concerns with a qualified clinician.</div>')
