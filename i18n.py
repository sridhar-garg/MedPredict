"""Offline presentation-only localization. Never translate model values or user data."""
import functools
import json
import re
from html import escape, unescape
from pathlib import Path

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

LANGUAGES = {
    'en': 'English', 'hi': 'हिन्दी · Hindi', 'bn': 'বাংলা · Bengali',
    'mr': 'मराठी · Marathi', 'ta': 'தமிழ் · Tamil', 'te': 'తెలుగు · Telugu',
    'gu': 'ગુજરાતી · Gujarati', 'kn': 'ಕನ್ನಡ · Kannada', 'ml': 'മലയാളം · Malayalam',
    'pa': 'ਪੰਜਾਬੀ · Punjabi', 'es': 'Español · Spanish', 'fr': 'Français · French',
    'de': 'Deutsch · German', 'pt': 'Português · Portuguese', 'ar': 'العربية · Arabic',
}
ROOT = Path(__file__).parent / 'translations'

@functools.lru_cache(maxsize=16)
def catalog(language):
    path = ROOT / f'{language}.json'
    return json.loads(path.read_text()) if path.exists() else {}


def t(value):
    if not isinstance(value, str) or st.session_state.get('mp_language', 'en') == 'en':
        return value
    entries = catalog(st.session_state.get('mp_language', 'en'))
    stripped = value.strip()
    if stripped in entries:
        return value.replace(stripped, entries[stripped], 1)
    # Preserve emoji, numbering and Markdown around known interface labels.
    for prefix, suffix in [('**','**'), ('### ','')]:
        if stripped.startswith(prefix) and (not suffix or stripped.endswith(suffix)):
            inner = stripped[len(prefix):len(stripped)-len(suffix) if suffix else None]
            if inner in entries:
                return prefix + entries[inner] + suffix
    for word in sorted(entries, key=len, reverse=True):
        # Translate a complete label with decorative emoji, numbering or arrows.
        # Keep uncovered sentences intact instead of mixing two languages mid-sentence.
        if word in value:
            before, _, after = value.partition(word)
            if not re.search(r'[^\W\d_]', before + after):
                return before + entries[word] + after
    return value


def translate_markup(value):
    if not isinstance(value, str):
        return value
    # Styles, scripts, SVG, attributes and URLs must remain byte-for-byte intact.
    blocks = re.split(r'(<(?:style|script|svg)\b.*?</(?:style|script|svg)>)', value, flags=re.S|re.I)
    for i in range(0, len(blocks), 2):
        chunks = re.split(r'(<[^>]+>)', blocks[i])
        for j in range(0, len(chunks), 2):
            source = unescape(chunks[j])
            chunks[j] = escape(t(source), quote=False) if t(source) != source else chunks[j]
        blocks[i] = ''.join(chunks)
    return ''.join(blocks)


def install_translations():
    if getattr(DeltaGenerator, '_mp_localized', False):
        return
    # Widget options keep their original values: predictions and if/else routing stay identical.
    for name in ('selectbox', 'multiselect', 'radio', 'select_slider'):
        original = getattr(DeltaGenerator, name)
        def make_options(fn):
            @functools.wraps(fn)
            def wrapped(self, *args, **kwargs):
                args = list(args)
                if args:
                    args[0] = t(args[0])
                elif 'label' in kwargs:
                    kwargs['label'] = t(kwargs['label'])
                formatter = kwargs.get('format_func', str)
                kwargs['format_func'] = lambda item: t(formatter(item))
                return fn(self, *args, **kwargs)
            return wrapped
        setattr(DeltaGenerator, name, make_options(original))
    for name in ('title','header','subheader','caption','markdown','html','info','success','warning','error',
                 'button','form_submit_button','checkbox','toggle','text_input','text_area','number_input',
                 'slider','file_uploader','chat_input','download_button','expander','metric','page_link','tabs','popover'):
        original = getattr(DeltaGenerator, name)
        def make_text(fn, method):
            @functools.wraps(fn)
            def wrapped(self, *args, **kwargs):
                if kwargs.pop('_mp_raw', False):
                    return fn(self, *args, **kwargs)
                args = list(args)
                index = 1 if method == 'page_link' else 0
                convert = translate_markup if method in ('markdown','html') else t
                if method == 'tabs':
                    if args: args[0] = [t(x) for x in args[0]]
                    elif 'tabs' in kwargs: kwargs['tabs'] = [t(x) for x in kwargs['tabs']]
                elif len(args) > index:
                    args[index] = convert(args[index])
                else:
                    for key in ('body','label'):
                        if key in kwargs: kwargs[key] = convert(kwargs[key])
                for key in ('help','placeholder'):
                    if key in kwargs: kwargs[key] = t(kwargs[key])
                return fn(self, *args, **kwargs)
            return wrapped
        setattr(DeltaGenerator, name, make_text(original, name))
    # Streamlit's top-level functions are bound method aliases, so rebind those too.
    for name in ('selectbox','multiselect','radio','select_slider','title','header','subheader','caption',
                 'markdown','html','info','success','warning','error','button','form_submit_button',
                 'checkbox','toggle','text_input','text_area','number_input','slider','file_uploader',
                 'chat_input','download_button','expander','metric','page_link','tabs','popover'):
        setattr(st, name, getattr(st._main, name))
    DeltaGenerator._mp_localized = True


def load_account_preferences():
    user_id = st.session_state.get('user_id')
    if user_id and st.session_state.get('_mp_preferences_user') != user_id:
        from database import load_preferences
        preferences = load_preferences(user_id)
        st.session_state['mp_language'] = preferences.get('language', st.session_state.get('mp_language', 'en'))
        st.session_state['healthai_theme'] = preferences.get('theme', 'light')
        st.session_state['mp_dark_mode'] = st.session_state['healthai_theme'] == 'dark'
        st.session_state['_mp_preferences_user'] = user_id


def persist_preferences():
    if st.session_state.get('user_id'):
        from database import save_preferences
        save_preferences(st.session_state.user_id, st.session_state.get('mp_language','en'),
                         st.session_state.get('healthai_theme','light'))


def language_picker(key='mp_language_picker'):
    install_translations()
    st.session_state.setdefault('mp_language','en')
    # The same preference is available on sign-in and inside the workspace.
    if st.session_state.get(key) != st.session_state.mp_language:
        st.session_state[key] = st.session_state.mp_language
    def changed():
        st.session_state['mp_language'] = st.session_state[key]
        persist_preferences()
    st.selectbox('Language', list(LANGUAGES),
                 index=list(LANGUAGES).index(st.session_state.mp_language),
                 format_func=lambda code: LANGUAGES[code], key=key, on_change=changed)
    if st.session_state.mp_language != 'en':
        st.caption('Interface language selected. Specialist medical terms and research text may remain in English.')
