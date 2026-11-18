import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import database as db
import google_auth as google
from auth import create_account, authenticate_user

CLIENT = "test-client.apps.googleusercontent.com"


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MEDPREDICT_DB_PATH", str(tmp_path / "google.db"))
    db.initialize_database()


def claims(**changes):
    value = dict(iss="https://accounts.google.com", sub="google-subject-1",
                 email="visitor@gmail.com", email_verified=True, aud=CLIENT,
                 name="Test Visitor", iat=time.time() - 5, exp=time.time() + 1800)
    value.update(changes)
    return value


@pytest.mark.parametrize("changes", [
    {"iss": "https://untrusted.example"}, {"aud": "another-client"},
    {"azp": "another-client"}, {"email_verified": False},
    {"email_verified": 1}, {"sub": ""}, {"exp": 0},
    {"exp": float("nan")}, {"iat": time.time() + 10000},
])
def test_rejects_invalid_or_expired_identity(changes):
    with pytest.raises(ValueError):
        google.identity_from_claims(claims(**changes), CLIENT)


def test_google_subject_preserves_history_when_email_changes(database):
    identity = google.identity_from_claims(claims(), CLIENT)
    user = google.google_user(identity)
    db.save_workspace_item(user[0], "Reports", "Test result", {"value": 42})
    again = google.google_user(google.GoogleIdentity(identity.subject, "new@gmail.com", "New name"))
    assert again[0] == user[0]
    assert db.get_workspace_items(again[0])[0]["payload"]["value"] == 42
    other = google.google_user(google.GoogleIdentity("subject-2", "other@gmail.com", "Other"))
    assert db.get_workspace_items(other[0]) == []
    assert authenticate_user(user[3], "any-password") is None


def test_existing_account_is_not_silently_merged(database):
    user = create_account("visitor@gmail.com", "visitor", "Existing-Password-2026")
    other = create_account("other@example.com", "other", "Other-Password-2026")
    db.save_workspace_item(user, "Reports", "Private result", {"private": True})
    identity = google.identity_from_claims(claims(), CLIENT)
    with pytest.raises(google.GoogleAccountLinkRequired):
        google.google_user(identity)
    with pytest.raises(google.GoogleAccountLinkRequired):
        google.google_user(identity, link_user_id=other)
    assert google.google_user(identity, link_user_id=user)[0] == user
    assert google.google_user(identity)[0] == user
    assert db.get_workspace_items(user)[0]["payload"]["private"] is True


def test_google_account_cannot_be_connected_to_a_second_user(database):
    first = google.google_user(google.identity_from_claims(claims(), CLIENT))
    other = create_account("other@example.com", "other", "Other-Password-2026")
    with pytest.raises(ValueError):
        google.google_user(google.identity_from_claims(claims(), CLIENT), link_user_id=other)
    assert google.google_user(google.identity_from_claims(claims(), CLIENT))[0] == first[0]


def test_unconfigured_google_keeps_password_login_available(database):
    user = create_account("local@example.com", "local_user", "Local-Password-2026")
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=20).run()
    assert not app.exception
    assert app.button(key="continue_google").disabled
    app.text_input(key="login_username").set_value("local_user")
    app.text_input(key="login_password").set_value("Local-Password-2026")
    app.button(key="login_with_password").click().run()
    assert not app.exception
    assert app.session_state["user_id"] == user
    assert app.session_state["auth_method"] == "password"


def test_configured_button_starts_native_google_oidc(database, monkeypatch):
    calls = []
    monkeypatch.setattr(google, "google_config", lambda settings=None: {"client_id": CLIENT})
    monkeypatch.setattr(google.st, "login", lambda provider: calls.append(provider))
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=20).run()
    assert not app.button(key="continue_google").disabled
    app.button(key="continue_google").click().run()
    assert not app.exception
    assert calls == ["google"]


def test_callback_restores_account_and_logout_removes_identity_cookie(database, monkeypatch):
    class Cookie:
        logged_in = True

        def to_dict(self):
            return {"is_logged_in": self.logged_in, **claims()}

    cookie = Cookie()
    monkeypatch.setattr(google, "google_config", lambda settings=None: {"client_id": CLIENT})
    monkeypatch.setattr(google.st, "user", cookie)
    logouts = []

    def end_google_session():
        cookie.logged_in = False
        logouts.append(True)
        google.st.switch_page("app.py")

    monkeypatch.setattr(google.st, "logout", end_google_session)
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=20).run()
    assert not app.exception
    user = app.session_state["user_id"]
    assert app.session_state["auth_method"] == "google"
    db.save_workspace_item(user, "Reports", "Google user's work", {"saved": True})
    fresh = AppTest.from_file(Path("app.py").resolve(), default_timeout=20).run()
    assert fresh.session_state["user_id"] == user
    assert db.get_workspace_items(user)[0]["payload"]["saved"] is True
    fresh.session_state["private_result"] = "synthetic private result"
    fresh.switch_page("pages/profile.py").run()
    fresh.button(key="profile_logout").click().run()
    assert not fresh.exception
    assert logouts == [True]
    assert not fresh.session_state["is_logged_in"]
    assert "private_result" not in fresh.session_state


def test_configuration_rejects_wrong_provider_and_unsafe_callback():
    config = {"auth": {"redirect_uri": "https://example.com/oauth2callback",
                       "cookie_secret": "x" * 48, "google": {
                           "client_id": CLIENT, "client_secret": "test-only-secret",
                           "server_metadata_url": google.GOOGLE_METADATA}}}
    assert google.google_config(config) is not None
    config["auth"]["redirect_uri"] = "http://public.example/oauth2callback"
    assert google.google_config(config) is None
    config["auth"]["redirect_uri"] = "https://example.com/oauth2callback"
    config["auth"]["google"]["server_metadata_url"] = "https://untrusted.example/oidc"
    assert google.google_config(config) is None
