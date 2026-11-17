"""Shared presentation helpers for the MedPredict Streamlit interface."""
import base64
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

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
    return (f'<div class="mp-brand"><span class="mp-brand-mark">{icon("pulse")}</span>'
            '<span>MedPredict<span class="mp-brand-dot">.</span></span></div>')


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
    html(f'<span class="mp-theme-marker healthai-theme-{theme}-marker" data-ui-revision="sidebar-chat-3" aria-hidden="true"></span>')


def _change_theme():
    st.session_state.healthai_theme = "dark" if st.session_state.mp_dark_mode else "light"


def theme_switch():
    st.toggle("Dark appearance", value=st.session_state.get("healthai_theme") == "dark",
              key="mp_dark_mode", on_change=_change_theme)


def section(title, description="", eyebrow=""):
    html(f'<div class="mp-section"><span class="mp-eyebrow">{escape(eyebrow)}</span>'
         f'<h2>{escape(title)}</h2><p>{escape(description)}</p></div>')


def tool_card(name, description, glyph, page, key, color="violet", label="Open tool"):
    with st.container(border=True):
        html(f'<div class="mp-tool-card"><span class="mp-icon mp-{escape(color)}">{icon(glyph)}</span>'
             f'<h3>{escape(name)}</h3><p>{escape(description)}</p></div>')
        if st.button(f"{label}  →", key=key, use_container_width=True):
            st.switch_page(page)
