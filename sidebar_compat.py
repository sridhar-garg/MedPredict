"""Stable, labelled native navigation for the original MedPredict layout."""
from pathlib import Path
import streamlit as st

_LINKS = [
    ("app.py", "Dashboard", "space_dashboard"),
    ("pages/diabetes_app.py", "Diabetes", "water_drop"),
    ("pages/heart_app.py", "Heart health", "favorite"),
    ("pages/breast_app.py", "Breast health", "health_and_safety"),
    ("pages/4_health_screenings.py", "More screenings", "health_metrics"),
    ("pages/5_medical_imaging.py", "Imaging & reports", "radiology"),
    ("pages/8_gemini_chatbot.py", "AI assistant", "chat_bubble_outline"),
    ("pages/10_disease_atlas.py", "Disease atlas", "menu_book"),
    ("pages/9_abilitybridge.py", "Accessibility tools", "accessibility_new"),
    ("pages/12_reviews.py", "Reviews", "rate_review"),
    ("pages/history.py", "Assessment history", "history"),
    ("pages/z_family.py", "Family health", "group"),
    ("pages/profile.py", "My profile", "person_outline"),
]


def show_sidebar():
    st.markdown('''<style>
    [data-testid="stSidebarNav"] {display:none !important}
    html body:has(.mp-legacy-brand) section[data-testid="stSidebar"]::before {display:none !important; content:none !important}
    [data-testid="stSidebarUserContent"] {padding:20px 16px !important}
    .mp-legacy-brand {font-size:22px; font-weight:800; color:#173653; margin:0 0 18px}
    body:has(.healthai-theme-dark-marker) .mp-legacy-brand {color:#e0ebf7}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a {padding:9px 12px; border-radius:10px}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a p {font-size:14px !important; color:#28465f !important; font-weight:600}
    body:has(.healthai-theme-dark-marker) [data-testid="stSidebar"] [data-testid="stPageLink"] a p,
    body:has(.healthai-theme-dark-marker) [data-testid="stSidebar"] [data-testid="stPageLink"] a span {color:#d7e3f2 !important}
    </style>''', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="mp-legacy-brand">MedPredict</div>',unsafe_allow_html=True)
        for path, label, glyph in _LINKS:
            if (Path(__file__).parent / path).exists():
                st.page_link(path,label=label,icon=f":material/{glyph}:")
