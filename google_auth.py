"""Google OIDC sign-in, using Streamlit's verified identity cookie.

Only st.user supplies identity claims. Query strings, form fields and browser
storage are never accepted as an authenticated Google identity.
"""
from dataclasses import dataclass
from hashlib import sha256
import math
import sqlite3
import time
from urllib.parse import urlparse

import streamlit as st

from database import get_connection

GOOGLE_METADATA = "https://accounts.google.com/.well-known/openid-configuration"


class GoogleAccountLinkRequired(ValueError):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str


def google_config(settings=None):
    """Return valid server-side configuration, or None without exposing secrets."""
    try:
        auth = (st.secrets if settings is None else settings).get("auth", {})
        provider = auth.get("google", {})
        redirect = urlparse(auth.get("redirect_uri", ""))
        if redirect.path != "/oauth2callback" or redirect.query or redirect.fragment:
            return None
        if redirect.scheme != "https" and not (
            redirect.scheme == "http" and redirect.hostname in ("localhost", "127.0.0.1")
        ):
            return None
        cookie_secret = auth.get("cookie_secret", "")
        if not redirect.hostname or len(cookie_secret) < 32 or cookie_secret.startswith("REPLACE_"):
            return None
        if provider.get("server_metadata_url") != GOOGLE_METADATA:
            return None
        if not provider.get("client_id", "").endswith(".apps.googleusercontent.com"):
            return None
        secret = provider.get("client_secret", "")
        if not secret or secret.startswith("REPLACE_"):
            return None
        return provider
    except (FileNotFoundError, KeyError, TypeError, AttributeError, ValueError):
        return None


def identity_from_claims(claims, client_id, now=None):
    """Validate claims already verified by Streamlit/Authlib's OIDC exchange."""
    now = time.time() if now is None else now
    if claims.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
        raise ValueError("Google did not confirm this sign-in.")
    audience = claims.get("aud")
    if client_id not in ([audience] if isinstance(audience, str) else audience or []):
        raise ValueError("This sign-in belongs to a different application.")
    if claims.get("azp", client_id) != client_id:
        raise ValueError("This sign-in belongs to a different application.")
    try:
        expiry, issued = float(claims["exp"]), float(claims["iat"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Please sign in with Google again.") from None
    if not math.isfinite(expiry) or not math.isfinite(issued) or expiry <= now or issued > now + 60:
        raise ValueError("Your Google sign-in has expired. Please sign in again.")
    subject = claims.get("sub")
    email = claims.get("email")
    if (not isinstance(subject, str) or not subject or len(subject) > 255
            or not isinstance(email, str) or len(email) > 254 or email.count("@") != 1
            or not (claims.get("email_verified") is True or claims.get("email_verified") == "true")):
        raise ValueError("Google must confirm a verified email address to continue.")
    return GoogleIdentity(subject, email.strip().lower(), str(claims.get("name", ""))[:120])


def google_user(identity, *, link_user_id=None):
    """Resolve stable Google subject; link an existing account only after local login."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM google_identities WHERE subject=?", (identity.subject,))
        mapped = cur.fetchone()
        if mapped:
            if link_user_id is not None and link_user_id != mapped[0]:
                raise ValueError("This Google account is already connected to another account.")
            user_id = mapped[0]
        else:
            cur.execute("SELECT id FROM users WHERE LOWER(email)=?", (identity.email,))
            existing = cur.fetchone()
            if existing:
                if existing[0] != link_user_id:
                    raise GoogleAccountLinkRequired(
                        "An account already uses this email. Sign in with its username and password once to connect Google and keep your saved work."
                    )
                user_id = existing[0]
            else:
                if link_user_id is not None:
                    raise ValueError("Use the Google account with the same email as your MedPredict account.")
                username = "google_" + sha256(identity.subject.encode()).hexdigest()[:20]
                cur.execute("INSERT INTO users(email,name,username,password_hash) VALUES(?,?,?,?)",
                            (identity.email, identity.name, username, None))
                user_id = cur.lastrowid
            cur.execute("INSERT INTO google_identities(subject,user_id) VALUES(?,?)",
                        (identity.subject, user_id))
        cur.execute("SELECT id,email,name,username,created_at FROM users WHERE id=?", (user_id,))
        profile = cur.fetchone()
        if profile is None:
            raise ValueError("This account is no longer available.")
        conn.commit()
        return profile
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError("This account could not be connected. Please sign in again.") from None
    finally:
        conn.close()


def _current_identity():
    config = google_config()
    if config is None or not st.user.to_dict().get("is_logged_in", False):
        return None
    return identity_from_claims(st.user.to_dict(), config["client_id"])


def restore_google_login():
    if st.session_state.get("is_logged_in") and st.session_state.get("auth_method") != "google":
        return
    try:
        identity = _current_identity()
        if identity is None:
            if st.session_state.get("auth_method") == "google":
                clear_login_session()
            return
        user = google_user(identity)
    except GoogleAccountLinkRequired as exc:
        st.session_state["google_link_pending"] = True
        st.session_state["google_login_message"] = str(exc)
        return
    except ValueError:
        clear_login_session()
        st.logout()
        st.stop()
    except Exception:
        st.session_state["is_logged_in"] = False
        st.session_state["google_login_message"] = "Google sign-in could not be completed. Please try again or use your username."
        return
    if st.session_state.get("user_id") != user[0]:
        clear_login_session()
    st.session_state.update(is_logged_in=True, user_id=user[0], user_email=user[1],
                            verified=True, auth_method="google")
    st.session_state.pop("google_login_message", None)
    st.session_state.pop("google_link_pending", None)


def connect_pending_google(user_id):
    if not st.session_state.get("google_link_pending"):
        return
    identity = _current_identity()
    if identity is None:
        raise ValueError("Please sign in with Google again before connecting your account.")
    google_user(identity, link_user_id=user_id)
    st.session_state.pop("google_link_pending", None)
    st.session_state.pop("google_login_message", None)


def render_google_login():
    with st.container(key="google_login"):
        configured = google_config() is not None
        if st.button("Continue with Google", icon=":material/account_circle:",
                     disabled=not configured, use_container_width=True, key="continue_google"):
            st.login("google")
        if not configured:
            st.caption("Google sign-in is not available yet. You can use your username below.")
        if st.session_state.get("google_login_message"):
            st.info(st.session_state.google_login_message)
        st.markdown('<div class="mp-auth-divider"><span>or use your username</span></div>', unsafe_allow_html=True)


def clear_login_session():
    for key in list(st.session_state):
        if key not in ("mp_language", "healthai_theme"):
            del st.session_state[key]


def logout():
    google_cookie = bool(st.user.to_dict().get("is_logged_in", False))
    clear_login_session()
    if google_cookie:
        st.logout()
        st.stop()
    st.switch_page("app.py")
