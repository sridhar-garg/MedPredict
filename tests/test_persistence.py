import json
import sqlite3
import subprocess
import sys

import pytest

import database as db
from auth import create_account, authenticate_user

@pytest.fixture
def accounts(tmp_path,monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.setenv('MEDPREDICT_DB_PATH',str(tmp_path/'test.db'))
    db.initialize_database()
    a=create_account('a@example.com','alice','Strong-Test-2026',name='Alice')
    b=create_account('b@example.com','bob','Strong-Test-2026',name='Bob')
    return a,b


def test_review_survives_new_process_and_login(accounts):
    a,b=accounts
    db.save_review(a,'Alice',4,'Clear navigation','The navigation was easy to follow.','Dashboard')
    db.save_review(a,'Alice',5,'Even clearer','The new layout is easy to read.','Accessibility tools')
    result=subprocess.check_output([sys.executable,'-c',
        "import json; from auth import authenticate_user; from database import get_reviews; u=authenticate_user('alice','Strong-Test-2026'); print(json.dumps(get_reviews(u[0])))"],text=True)
    rows=json.loads(result)
    assert len(rows)==1 and rows[0]['rating']==5 and rows[0]['name']=='Alice'
    assert db.get_reviews(b)==[]
    db.delete_review(b)
    assert len(db.get_reviews())==1
    db.delete_review(a)
    assert db.get_reviews()==[]


def test_private_workspace_isolation_and_restart(accounts):
    a,b=accounts
    for kind in ('Screenings','Reports','Imaging','AI assistant','Accessibility tools'):
        db.save_workspace_item(a,kind,'Saved result',{'text':'नमस्ते ⠓⠑','number':3.5})
    assert db.get_workspace_items(b)==[]
    item=db.get_workspace_items(a)[0]
    db.delete_workspace_item(b,item['id'])
    assert len(db.get_workspace_items(a))==5
    db.delete_workspace_item(a,item['id'])
    assert len(db.get_workspace_items(a))==4
    db.initialize_database()
    assert len(db.get_workspace_items(a))==4


def test_assessments_family_permissions_and_preferences(accounts):
    a,b=accounts
    assert db.save_health_assessment(a,'Diabetes',{'Age':40},'Example',.2,'Educational result')
    assert db.get_health_assessments(b)==[]
    assert db.get_family_assessments(b,a)==[]
    assert db.add_family_connection(a,b,'Sibling')[0]
    request=db.get_pending_family_requests(b)[0][0]
    assert not db.accept_family_connection(request,a)
    assert db.accept_family_connection(request,b)
    assert len(db.get_family_assessments(b,a))==1
    assert db.revoke_family_connection(request,b)
    assert db.get_family_assessments(b,a)==[]
    db.save_preferences(a,'hi','dark')
    assert db.load_preferences(a)==dict(language='hi',theme='dark')
    assert db.load_preferences(b)=={}


def test_review_validation_and_database_constraints(accounts):
    a,b=accounts
    with pytest.raises(ValueError): db.save_review(None,'A',5,'Hi','Hello','Dashboard')
    with pytest.raises(ValueError): db.save_review(a,'Alice',8,'Good','Enough comment text','Dashboard')
    with pytest.raises(ValueError): db.save_review(a,'Alice',5,'Good','short','Dashboard')
    with pytest.raises(sqlite3.IntegrityError): db.save_workspace_item(9999,'Reports','test',{})
