"""Shared presentation helpers for the MedPredict Streamlit interface."""
import base64
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

# One colour family follows each tool from its dashboard card to its own page.
PAGE_CONTEXT = {
    "app": ("teal", "", "", "pulse"),
    "heart_app": ("coral", "HEART HEALTH", "Explore cardiovascular measurements and the factors behind the estimate.", "heart"),
    "diabetes_app": ("blue", "DIABETES", "Bring symptoms and health indicators into a clearer picture.", "drop"),
    "breast_app": ("rose", "BREAST CANCER", "Understand model estimates from diagnostic measurements.", "ribbon"),
    "4_health_screenings": ("amber", "EVERYDAY SCREENINGS", "Check measurements with transparent, source-linked screening tools.", "pulse"),
    "5_medical_imaging": ("slate", "IMAGING & REPORTS", "Explore scans and report measurements in a focused workspace.", "scan"),
    "8_gemini_chatbot": ("violet", "AI ASSISTANT", "Ask questions, understand unfamiliar terms and revisit conversations.", "chat"),
    "9_abilitybridge": ("teal", "ACCESSIBILITY", "Communicate with fingerspelling and explore Braille within MedPredict.", "access"),
    "10_disease_atlas": ("olive", "HEALTH KNOWLEDGE", "Find context and learn from medically sourced information.", "book"),
    "history": ("copper", "YOUR SAVED WORK", "Return to your assessments, reports and saved conversations.", "history"),
    "z_family": ("green", "FAMILY HEALTH", "Keep family connections and sharing permissions in one place.", "people"),
    "profile": ("cyan", "YOUR ACCOUNT", "Manage your profile, sign-in details and personal preferences.", "shield"),
    "12_reviews": ("gold", "COMMUNITY", "Read real visitor feedback and share your experience.", "people"),
}

PAGE_DESIGNS = {
    "heart_app": ("cardio", "Heart health", "Clinical measurements · Model comparison · Explainable factors", "pulse"),
    "diabetes_app": ("metabolic", "Diabetes assessment", "Symptoms and indicators · A structured view of your information", "drop"),
    "breast_app": ("breast", "Breast cancer", "Diagnostic measurements · Clear explanations · Your saved results", "ribbon"),
    "4_health_screenings": ("screening", "Check the numbers that matter.", "Seven practical screening tools, with their sources and calculations.", "07"),
    "5_medical_imaging": ("imaging", "A clearer view of your reports.", "A focused workspace for medical images and report measurements.", "scan"),
    "8_gemini_chatbot": ("conversation", "Ask. Understand. Explore.", "A conversation space for health information and questions.", "chat"),
    "9_abilitybridge": ("access", "More ways to communicate.", "Fingerspelling and Braille tools, designed to be easy to reach.", "⠿"),
    "10_disease_atlas": ("library", "Conditions, clearly explained.", "Browse common conditions and explore source-linked health information.", "A–Z"),
    "history": ("timeline", "Your health timeline.", "Assessments, reports and conversations, ready when you return.", "history"),
    "z_family": ("family", "Care, connected.", "Your family circle, invitations and sharing permissions.", "people"),
    "profile": ("account", "Your personal space.", "Profile, sign-in details and preferences in one place.", "shield"),
    "12_reviews": ("community", "Your voice makes a difference.", "Read community feedback and share your experience.", "“"),
}

_ICONS = {
    "arrow": '<path d="M7 17 17 7M7 7h10v10"/>',
    "pulse": '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
    "heart": '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
    "drop": '<path d="M12 3C9 7 5 11 5 15a7 7 0 0 0 14 0c0-4-4-8-7-12Z"/><path d="M8 15a4 4 0 0 0 4 4"/>',
    "ribbon": '<path d="m8 21 8-13a4.5 4.5 0 0 0-8 0l8 13M8 8c2 2 6 2 8 0"/>',
    "scan": '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M7 12h10M12 7v10"/>',
    "book": '<path d="M12 5v16M3 3c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2Z"/>',
    "chat": '<path d="M21 11a9 9 0 0 1-9 9 10 10 0 0 1-4-.9L3 21l1.9-5A9 9 0 1 1 21 11Z"/><path d="M8 11h.01M12 11h.01M16 11h.01"/>',
    "flask": '<path d="M9 3h6M10 3v7L4 19a1.3 1.3 0 0 0 1 2h14a1.3 1.3 0 0 0 1-2l-6-9V3M7 15h10"/>',
    "history": '<path d="M3 11a9 9 0 1 1 2.7 7M3 4v7h7M12 7v5l3 2"/>',
    "people": '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6M21 21v-3a6 6 0 0 0-4-5"/>',
    "access": '<circle cx="12" cy="4" r="2"/><path d="m4 9 8 2 8-2M12 11v5m0 0-5 6m5-6 5 6"/>',
    "spark": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5ZM20 2v4m-2-2h4"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
}


def icon(name, size=24):
    return (f'<svg width="{int(size)}" height="{int(size)}" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_ICONS.get(name, _ICONS["pulse"])}</svg>')


def html(markup):
    # Avoid Markdown interpreting indented HTML as a code block.
    st.markdown("\n".join(line.lstrip() for line in markup.splitlines()), unsafe_allow_html=True)


def brand():
    return (f'<div class="mp-brand"><span class="mp-brand-mark">{brand_mark()}</span>'
            '<span>MedPredict<span class="mp-brand-dot">.</span></span></div>')


def brand_mark():
    return ('<svg viewBox="0 0 64 64" width="34" height="34" fill="none" aria-hidden="true">'
            '<path d="M23 19v-5a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v5" stroke="#e5deff" stroke-width="4"/>'
            '<rect x="9" y="19" width="46" height="36" rx="10" fill="#fff"/>'
            '<path d="M32 27v20M22 37h20" stroke="#096961" stroke-width="5" stroke-linecap="round"/>'
            '<circle cx="49" cy="22" r="8" fill="#7ee5cc"/>'
            '<path d="m45 22 3 3 5-6" stroke="#194d44" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>')


@lru_cache(maxsize=1)
def studio_image():
    return "data:image/webp;base64," + base64.b64encode(
        (ROOT / "assets" / "medpredict-studio.webp").read_bytes()
    ).decode("ascii")


def apply_theme():
    st.session_state.setdefault("healthai_theme", "light")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    theme = st.session_state.healthai_theme
    language = st.session_state.get("mp_language", "en")
    html(f'<span class="mp-locale" data-language="{escape(language)}" lang="{escape(language)}"></span>')
    html(f'<span class="mp-theme-marker healthai-theme-{theme}-marker" data-ui-revision="mobile-header-8" aria-hidden="true"></span>')


def _change_theme():
    st.session_state.healthai_theme = "dark" if st.session_state.mp_dark_mode else "light"
    from i18n import persist_preferences
    persist_preferences()


def theme_switch():
    st.toggle("Dark mode", value=st.session_state.get("healthai_theme") == "dark",
              key="mp_dark_mode", on_change=_change_theme)


def section(title, description="", eyebrow=""):
    html(f'<div class="mp-section"><span class="mp-eyebrow">{escape(eyebrow)}</span>'
         f'<h2>{escape(title)}</h2><p>{escape(description)}</p></div>')


def page_header(route):
    design, title, copy, symbol = PAGE_DESIGNS[route]
    tone, label, _, _ = PAGE_CONTEXT[route]
    art = icon(symbol, 110) if symbol in _ICONS else escape(symbol)
    html(f'<header class="mp-page-hero mp-design-{design}" data-tone="{tone}">'
         f'<div class="mp-page-hero-copy"><span class="mp-hero-kicker">MEDPREDICT / {label}</span>'
         f'<h1>{title}</h1><p>{copy}</p></div><div class="mp-page-hero-art" aria-hidden="true">{art}</div></header>')


def assessment_workflow(steps):
    cards = ''.join(f'<li><span class="mp-process-number">{escape(number)}</span>'
                    f'<h3>{escape(title)}</h3><p>{escape(copy)}</p></li>' for number, title, copy in steps)
    html('<section class="mp-workflow"><div class="mp-workflow-heading"><span class="mp-eyebrow">THE PROCESS</span>'
         '<h2>How this assessment works</h2><p>Follow your information from input to explanation.</p></div>'
         f'<ol class="mp-process-grid">{cards}</ol></section>')


def tool_card(name, description, glyph, page, key, color="violet", label="Open tool"):
    category = {
        "open_diabetes": "ASSESSMENT / 01", "open_heart": "ASSESSMENT / 02",
        "open_breast": "ASSESSMENT / 03", "mp_ax_open_ability": "COMMUNICATE & CONVERT",
        "open_addon_screenings": "MEASURE & CHECK", "open_addon_imaging": "SCAN & READ",
        "medpredict_gemini38_home": "ASK & UNDERSTAND", "mp_ax_open_atlas": "LEARN & EXPLORE",
        "mp_open_history": "YOUR SAVED RESULTS", "mp_open_family": "CONNECTED WITH PERMISSION",
        "mp_open_reviews": "COMMUNITY FEEDBACK",
    }.get(key, "YOUR WORKSPACE")
    with st.container(border=True, key=f"tool_{key}"):
        html(f'<div class="mp-tool-card mp-card-{escape(color)}"><span class="mp-icon mp-{escape(color)}">{icon(glyph)}</span>'
             f'<span class="mp-tool-type">{category}</span>'
             f'<h3>{escape(name)}</h3><p>{escape(description)}</p></div>')
        if st.button(f"{label}  →", key=key, use_container_width=True):
            st.switch_page(page)
