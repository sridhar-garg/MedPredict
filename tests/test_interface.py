from pathlib import Path
import json
import pyarrow as pa
import pytest

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


def test_dashboard_inserts_real_activity_between_existing_sections(tmp_path, monkeypatch):
    at, user = app(tmp_path, monkeypatch)
    markup = [item.value for item in at.markdown]
    order = [
        next(i for i, item in enumerate(markup) if item.startswith(prefix) and text in item)
        for prefix, text in (
            ('<section class="mp-hero"', 'Care a little better.'),
            ('<div class="mp-capabilities"', 'Your progress, together'),
            ('<div class="mp-tracking-heading"', 'Your health activity'),
            ('<div class="mp-section"', 'Where would you like to begin?'),
        )
    ]
    assert order == sorted(order)
    assert 'Explore assessments' in markup[order[0]]
    assert not at.get('vega_lite_chart')
    assert not any(link.proto.label == 'Start assessment' for link in at.get('page_link'))
    result_cards = [item.proto.body for item in at.get('html')
                    if item.proto.body.startswith('<article class="mp-tracking-result"')]
    assert len(result_cards) == 3
    assert all('No saved result yet' in card for card in result_cards)
    assert {'open_diabetes', 'open_heart', 'open_breast'} <= {button.key for button in at.button}

    for disease, score in (('Diabetes', .63), ('Diabetes', .71),
                           ('Heart Disease', .80), ('Heart Disease', .51), ('Breast Cancer', .60)):
        assert db.save_health_assessment(user, disease, {}, 'Synthetic result', score, '')
    db.save_workspace_item(user, 'Reports', 'My saved report', {})
    other = create_account('other-ui@example.com', 'other_ui_test', 'Interface-Test-2026')
    assert db.save_health_assessment(other, 'Diabetes', {}, 'Other result', .99, '')
    db.save_workspace_item(other, 'Reports', 'Other account report', {})
    at.run()
    assert not at.exception

    watch = next(item.value for item in at.markdown if item.value.startswith('<ul class="mp-watch-list"'))
    assert all(value in watch for value in ('71.00%', '63.00%', '+8.00 percentage points', '51.00%', '80.00%'))
    assert 'Earlier result above 60%' in watch
    assert 'Breast cancer' not in watch and '99.00%' not in watch
    recent = next(item.value for item in at.markdown if item.value.startswith('<ol class="mp-activity-timeline"'))
    assert recent.count('<li ') == 5
    latest = next(row for row in db.get_health_assessments(user) if row[1] == 'Diabetes')
    route = next(link.proto for link in at.get('page_link') if link.proto.label == 'View result')
    assert route.query_string.lstrip('?') == f'assessment={latest[0]}'

    def chart_rows(chart):
        return [row for data in chart.proto.datasets
                for row in pa.ipc.open_stream(data.data.data).read_all().to_pylist()]

    at.selectbox(key='tracking_estimate_condition').set_value('diabetes').run()
    trend, monthly = at.get('vega_lite_chart')
    assert [row['estimate'] for row in chart_rows(trend) if 'number' in row] == [.63, .71]
    assert sum(row['count'] for row in chart_rows(monthly)) == 6
    at.selectbox(key='dashboard_activity_filter').set_value('Reports').run()
    recent = next(item.value for item in at.markdown if item.value.startswith('<ol class="mp-activity-timeline"'))
    assert 'My saved report' in recent and 'Other account report' not in recent
    assert recent.count('<li ') == 1
    rows = chart_rows(at.get('vega_lite_chart')[1])
    assert {row['kind'] for row in rows} == {'Reports'} and sum(row['count'] for row in rows) == 1


def test_review_form_and_summary(tmp_path,monkeypatch):
    at,user=app(tmp_path,monkeypatch,'pages/12_reviews.py')
    assert not at.exception
    assert [tab.label for tab in at.tabs] == ['Community reviews', 'Write a review']
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


def test_atlas_search_selection_assistant_and_persistence(tmp_path,monkeypatch):
    import health_assistant
    monkeypatch.setattr(health_assistant,'load_settings',lambda *a,**kw: ('',health_assistant.DEFAULT_MODEL))
    at,user=app(tmp_path,monkeypatch,'pages/10_disease_atlas.py')
    assert not at.exception
    assert len(at.selectbox(key='atlas_topic_picker').options) >= 100
    next(x for x in at.text_input if x.label=='Search for a disease or condition').set_value('epilepsy')
    next(b for b in at.button if b.label=='Search conditions').click().run()
    assert not at.exception
    assert any('Epilepsy' in x.value and 'CONDITION GUIDE' in x.value for x in at.markdown)
    assert [tab.label for tab in at.tabs] == ['Overview','Symptoms & tests','Care & prevention']
    at.button(key='atlas_ask_assistant').click().run()
    assert not at.exception
    messages=at.session_state['medpredict_gemini_messages']
    assert messages[-1]['answer_mode']=='library'
    assert '### Epilepsy' in messages[-1]['content']
    assert db.get_workspace_items(user,'AI assistant')[0]['payload']['messages']==messages
    fresh=AppTest.from_file(Path('app.py').resolve(),default_timeout=20)
    fresh.session_state['is_logged_in']=True
    fresh.session_state['user_id']=user
    fresh.run().switch_page('pages/8_gemini_chatbot.py').run()
    assert not fresh.exception
    assert fresh.session_state['medpredict_gemini_messages']==messages


def test_atlas_related_screening_opens_the_correct_form(tmp_path,monkeypatch):
    at,_=app(tmp_path,monkeypatch,'pages/10_disease_atlas.py')
    next(x for x in at.text_input if x.label=='Search for a disease or condition').set_value('obesity')
    next(b for b in at.button if b.label=='Search conditions').click().run()
    assert not at.exception
    at.button(key='atlas_related_tool').click().run()
    assert not at.exception
    assert at.selectbox(key='mp_screening_picker').value=='Obesity / BMI'
    assert any(x.label=='Height (cm)' for x in at.number_input)


def test_chat_greeting_and_provider_retry(tmp_path,monkeypatch):
    import health_assistant as assistant
    monkeypatch.setattr(assistant,'load_settings',lambda *a,**kw: ('test-only-key',assistant.DEFAULT_MODEL))
    def unavailable(*a,**kw):
        raise RuntimeError('synthetic provider outage')
    monkeypatch.setattr(assistant,'generate_online_reply',unavailable)
    at,user=app(tmp_path,monkeypatch,'pages/8_gemini_chatbot.py')
    at.chat_input[0].set_value('hi').run()
    assert not at.exception
    assert at.session_state['medpredict_gemini_messages'][-1]['provider_unavailable']
    assert any('Hello!' in x.value for x in at.markdown)
    at.run()
    assert at.button(key='assistant_retry')
    monkeypatch.setattr(assistant,'generate_online_reply',lambda *a,**kw: assistant.AssistantAnswer('Hello from online AI.','online','test-model'))
    at.button(key='assistant_retry').click().run()
    assert not at.exception
    messages=at.session_state['medpredict_gemini_messages']
    assert len(messages)==2 and messages[-1]['answer_mode']=='online'
    assert db.get_workspace_items(user,'AI assistant')[0]['payload']['messages'][-1]['model']=='test-model'


@pytest.mark.parametrize('route,design', [('heart_app','cardio'),('diabetes_app','metabolic'),('breast_app','breast')])
def test_assessments_render_forms_and_the_compact_workflow(tmp_path,monkeypatch,route,design):
    at,_=app(tmp_path,monkeypatch,'pages/'+route+'.py')
    assert not at.exception and not at.error
    assert at.number_input or at.selectbox
    headers=[x.value for x in at.markdown if x.value.startswith('<header class="mp-page-hero')]
    assert len(headers)==1 and 'mp-design-'+design in headers[0]
    workflows=[x.value for x in at.markdown if x.value.startswith('<section class="mp-workflow')]
    assert len(workflows)==1 and workflows[0].count('<li>')==4
