from pathlib import Path
import json

from streamlit.testing.v1 import AppTest

import database as db
from auth import create_account


def app(tmp_path,monkeypatch,path='app.py'):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.setenv('MEDPREDICT_DB_PATH',str(tmp_path/'app.db'))
    db.initialize_database()
    user=create_account('ui@example.com','ui_test','Interface-Test-2026')
    at=AppTest.from_file(Path("app.py").resolve(),default_timeout=20)
    at.session_state['is_logged_in']=True
    at.session_state['user_id']=user
    at.run()
    if path != "app.py":
        at.switch_page(path).run()
    return at,user


def test_dashboard_accessibility_and_all_languages(tmp_path,monkeypatch):
    at,user=app(tmp_path,monkeypatch)
    assert not at.exception
    assert any(b.label=='Open accessibility tools  →' for b in at.button)
    for language in ('hi','bn','mr','ta','te','gu','kn','ml','pa','es','fr','de','pt','ar','en'):
        at.selectbox(key='mp_language_picker').set_value(language).run()
        assert not at.exception
        assert at.session_state['mp_language']==language
        assert db.load_preferences(user)['language']==language
    assert any('Your health, in focus.' in x.value for x in at.markdown)


def test_review_form_and_summary(tmp_path,monkeypatch):
    at,user=app(tmp_path,monkeypatch,'pages/12_reviews.py')
    assert not at.exception
    assert at.metric[0].value=='—'
    at.text_input[0].set_value('Visitor')
    at.text_input[1].set_value('Easy to navigate')
    at.text_area[0].set_value('I found the accessibility tools easy to discover.')
    at.checkbox[0].check()
    next(b for b in at.button if b.label=='Submit review').click().run()
    assert not at.exception
    assert at.metric[0].value=='5.0 / 5'
    assert len(db.get_reviews(user))==1
    assert any(b.label=='Update review' for b in at.button)


def test_screening_auto_save_and_history(tmp_path,monkeypatch):
    at,user=app(tmp_path,monkeypatch,'pages/4_health_screenings.py')
    assert not at.exception
    next(b for b in at.button if b.label=='Assess reading').click().run()
    assert not at.exception
    rows=db.get_workspace_items(user,'Screenings')
    assert len(rows)==1 and rows[0]['payload']['inputs']['sys']==120
    history=AppTest.from_file(Path('app.py').resolve(),default_timeout=20)
    history.session_state['is_logged_in']=True
    history.session_state['user_id']=user
    history.run()
    history.switch_page("pages/history.py").run()
    assert not history.exception
    assert any('High blood pressure' in x.label for x in history.expander)


def test_catalogs_share_keys_and_keep_technical_values():
    files=list(Path('translations').glob('*.json'))
    assert len(files)==14
    entries=[json.loads(p.read_text()) for p in files]
    assert all(set(d)==set(entries[0]) for d in entries)
    assert all(d['Dashboard'] and d['Accessibility tools'] for d in entries)
