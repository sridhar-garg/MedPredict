"""Shared native navigation for MedPredict's existing Streamlit pages."""
from inspect import currentframe
from pathlib import Path

import streamlit as st
from ui import brand, html, theme_switch, PAGE_CONTEXT, PAGE_DESIGNS, page_header


_NAV_GROUPS = [
    ("WORKSPACE", [
        ("app.py", "Dashboard", "space_dashboard"),
        ("pages/history.py", "Assessment history", "history"),
    ]),
    ("ASSESSMENTS", [
        ("pages/diabetes_app.py", "Diabetes", "water_drop"),
        ("pages/heart_app.py", "Heart health", "favorite"),
        ("pages/breast_app.py", "Breast cancer", "health_and_safety"),
        ("pages/4_health_screenings.py", "More screenings", "health_metrics"),
    ]),
    ("EXPLORE", [
        ("pages/5_medical_imaging.py", "Imaging & reports", "radiology"),
        ("pages/8_gemini_chatbot.py", "AI assistant", "chat_bubble_outline"),
        ("pages/10_disease_atlas.py", "Disease atlas", "menu_book"),
        ("pages/9_abilitybridge.py", "Accessibility tools", "accessibility_new"),
    ]),
    ("FEEDBACK", [
        ("pages/12_reviews.py", "Reviews", "rate_review"),
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

    from database import initialize_database
    from i18n import install_translations, load_account_preferences, language_picker
    install_translations()
    initialize_database()
    from google_auth import restore_google_login
    restore_google_login()
    load_account_preferences()
    tone, context_title, context_copy, context_icon = PAGE_CONTEXT.get(current_path.stem, ("teal", "", "", "pulse"))
    design = PAGE_DESIGNS.get(current_path.stem, ("dashboard",))[0]
    html(f'<span class="mp-route" data-route="{current_path.stem}" data-tone="{tone}" data-design="{design}" aria-hidden="true"></span>')
    with st.container(key="mp_workspace_header"):
        identity, menu, settings = st.columns([3, 1, 1], vertical_alignment="center", gap="small")
        with identity:
            html(brand())
        with menu:
            with st.popover("Menu", icon=":material/menu:", use_container_width=True):
                for heading, links in _NAV_GROUPS:
                    st.caption(heading)
                    for path, label, glyph in links:
                        st.page_link(path, label=label, icon=f":material/{glyph}:")
        with settings:
            with st.popover("Settings", icon=":material/tune:", use_container_width=True):
                language_picker()
                theme_switch()

    if current_path.stem in PAGE_DESIGNS:
        page_header(current_path.stem)

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
            html('<div class="mp-sidebar-note">Educational prototype<br>'
                 '<span>Not a medical diagnosis.</span></div>')
