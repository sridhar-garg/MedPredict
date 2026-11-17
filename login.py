import re
from pathlib import Path

import streamlit as st

from database import get_connection

from auth import (
    generate_otp,
    send_email_otp,
    get_user_by_email,
    create_account,
    authenticate_user,
    set_user_credentials,
)






def is_valid_email(email: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}$"
    return re.fullmatch(pattern, email) is not None






def _login_theme_changed():
    st.session_state.healthai_theme = (
        "light" if st.session_state.get("mp_light_switch", False) else "dark"
    )


def login_page():
    """A fresh premium sign-in experience; existing authentication remains unchanged."""
    defaults = {
        "otp_sent": False,
        "verified": False,
        "user_email": "",
        "otp": None,
        "user_id": None,
        "is_logged_in": False,
        "auth_mode": "Login",
        "otp_verified": False,
        "signup_existing_user": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("healthai_theme", "dark")

    design_file = Path(__file__).parent / "design_system.css"
    if design_file.is_file():
        st.markdown(f"<style>{design_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    brand_col, appearance_col = st.columns([6, 1.5], vertical_alignment="center")
    with brand_col:
        st.markdown('''
          <div class="mp-login-top" style="margin:0;border:0;padding:8px 0 15px">
            <div class="mp-brand-row">
              <span class="mp-brand-mark">✳</span>
              <div><div class="mp-brand-name">MedPredict</div>
                   <div class="mp-brand-sub">HEALTH RESEARCH, REIMAGINED</div></div>
            </div>
          </div>
        ''', unsafe_allow_html=True)
    with appearance_col:
        st.toggle(
            "Light mode",
            value=(st.session_state.healthai_theme == "light"),
            key="mp_light_switch",
            on_change=_login_theme_changed,
        )

    theme_marker = ("healthai-theme-light-marker" if st.session_state.healthai_theme == "light"
                    else "healthai-theme-dark-marker")
    st.markdown(
        f'<div class="mp-login-root {theme_marker}" style="display:none"></div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.07, .93], gap="large", vertical_alignment="center")
    with left:
        st.markdown('''
          <section class="mp-login-stage">
            <div class="mp-login-eyebrow">◈ &nbsp; MEDPREDICT PLATFORM / 01</div>
            <h1>Health intelligence.<br><span>A new perspective.</span></h1>
            <p class="mp-login-lead">Discover a clearer way to explore health screening models,
              understand research outputs, and learn how modern AI interprets data.
              Built for curiosity. Designed for clarity.</p>
            <div class="mp-login-visual">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 245" role="img"
                   aria-label="Abstract medical signal graphic, for illustration only">
                <defs>
                  <radialGradient id="login-glow"><stop stop-color="#53d5c5" stop-opacity=".2"/>
                    <stop offset="1" stop-color="#53d5c5" stop-opacity="0"/></radialGradient>
                  <linearGradient id="login-wave" x1="0" y1="0" x2="1" y2="0">
                    <stop stop-color="#55d4c7"/><stop offset=".55" stop-color="#76ead5"/>
                    <stop offset="1" stop-color="#8b9efb"/></linearGradient>
                </defs>
                <circle cx="290" cy="120" r="126" fill="url(#login-glow)"/>
                <g fill="none" stroke="#66889b" stroke-opacity=".25">
                  <circle cx="288" cy="121" r="42"/><circle cx="288" cy="121" r="75"/>
                  <circle cx="288" cy="121" r="106" stroke-dasharray="3 7"/>
                  <path d="M0 61H560M0 122H560M0 184H560M112 0V245M224 0V245M336 0V245M448 0V245"/>
                </g>
                <path d="M20 126H110L135 117L156 130L177 85L202 175L226 123H269L290 103L311 137L341 51L366 202L391 126H445L462 118L476 127H540"
                  fill="none" stroke="url(#login-wave)" stroke-width="5"
                  stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="341" cy="51" r="6" fill="#6ce1d0" stroke="#132331" stroke-width="3"/>
                <text x="22" y="28" fill="#89a6b4" font-size="11" font-family="Arial" letter-spacing="2">EXPLAINABLE SIGNALS</text>
                <text x="22" y="225" fill="#89a6b4" font-size="10" font-family="Arial">Concept illustration • No medical measurements</text>
              </svg>
            </div>
            <div class="mp-login-benefits">
              <span>◈ &nbsp; Research-driven</span><span>✧ &nbsp; Interactive tools</span>
              <span>↗ &nbsp; Clear explanations</span>
            </div>
          </section>
        ''', unsafe_allow_html=True)

    with right:
        with st.container(border=True):
            st.markdown('''
                <div class="mp-auth-pane" style="padding:9px 10px 0">
                  <div class="mp-auth-icon">✳</div>
                  <div class="mp-overline">YOUR WORKSPACE STARTS HERE</div>
                  <h2>Welcome to MedPredict.</h2>
                  <p class="mp-auth-sub">Sign in to continue, or create an account to explore the platform.</p>
                </div>
            ''', unsafe_allow_html=True)

            auth_mode = st.radio(
                "Choose an option",
                ["Login", "Create Account"],
                horizontal=True,
                key="auth_mode",
            )





            if auth_mode == "Login":



                if st.session_state.get("otp_sent", False):
                    st.session_state.otp_sent = False
                    st.session_state.otp = None
                    st.session_state.user_email = ""

                username = st.text_input(
                    "Username",
                    placeholder="Enter your username",
                    key="login_username",
                )

                password = st.text_input(
                    "Password",
                    placeholder="Enter your password",
                    type="password",
                    key="login_password",
                )

                if st.button(
                    "Login  →",
                    type="primary",
                    width="stretch",
                    key="login_with_password",
                ):

                    username = username.strip().lower()

                    if not username:
                        st.error("Please enter your username.")

                    elif not password:
                        st.error("Please enter your password.")

                    else:
                        user = authenticate_user(
                            username,
                            password
                        )

                        if user is None:
                            st.error(
                                "Incorrect username or password."
                            )
                        else:


                            st.session_state.user_id = user[0]
                            st.session_state.user_email = user[1]
                            st.session_state.is_logged_in = True
                            st.session_state.verified = True
                            st.session_state.otp = None
                            st.session_state.otp_sent = False

                            st.success("Login successful! 🎉")
                            st.rerun()





            else:





                if not st.session_state.get("otp_sent", False):

                    email = st.text_input(
                        "Email Address",
                        placeholder="you@example.com",
                        key="signup_email",
                    )

                    if st.button(
                        "Send OTP  →",
                        type="primary",
                        width="stretch",
                        key="send_signup_otp",
                    ):

                        email = email.strip().lower()

                        if not email:
                            st.error(
                                "Please enter your email address."
                            )

                        elif not is_valid_email(email):
                            st.error(
                                "Please enter a valid email address."
                            )

                        else:



                            existing_user = get_user_by_email(email)

                            otp = generate_otp()
                            st.session_state.otp = otp
                            st.session_state.user_email = email
                            st.session_state.signup_existing_user = (
                                existing_user is not None
                            )

                            with st.spinner(
                                "Sending verification code..."
                            ):
                                if send_email_otp(email, otp):
                                    st.session_state.otp_sent = True
                                    st.success(
                                        "OTP sent successfully! "
                                        "Check your email."
                                    )
                                    st.rerun()
                                else:
                                    st.session_state.otp = None
                                    st.session_state.user_email = ""
                                    st.session_state.signup_existing_user = False
                                    st.error(
                                        "Unable to send OTP. Please check "
                                        "your Gmail configuration and try again."
                                    )





                else:

                    st.divider()

                    st.markdown(
                        '<div class="verify-email-heading">'
                        'Verify your email</div>',
                        unsafe_allow_html=True,
                    )

                    st.info(
                        f"🔐 Verification code sent to "
                        f"**{st.session_state.user_email}**"
                    )

                    entered_otp = st.text_input(
                        "Enter 6-digit OTP",
                        max_chars=6,
                        placeholder="123456",
                        key="signup_otp",
                    )

                    verify_col, resend_col = st.columns(
                        2,
                        gap="small"
                    )

                    with verify_col:

                        if st.button(
                            "Verify OTP",
                            type="primary",
                            width="stretch",
                            key="verify_signup_otp",
                        ):

                            if entered_otp.strip() != str(
                                st.session_state.otp
                            ):
                                st.error(
                                    "Incorrect OTP. Please check your "
                                    "email and try again."
                                )
                            else:
                                st.session_state.otp_verified = True
                                st.session_state.otp = None
                                st.session_state.otp_sent = False
                                st.success(
                                    "Email verified successfully! 🎉"
                                )
                                st.rerun()

                    with resend_col:

                        if st.button(
                            "Resend OTP",
                            width="stretch",
                            key="resend_signup_otp",
                        ):

                            otp = generate_otp()
                            st.session_state.otp = otp

                            if send_email_otp(
                                st.session_state.user_email,
                                otp,
                            ):
                                st.success("New OTP sent!")
                            else:
                                st.error(
                                    "Unable to send OTP. Please try again."
                                )

                    if st.button(
                        "← Use a different email",
                        width="stretch",
                        key="change_signup_email",
                    ):
                        st.session_state.otp_sent = False
                        st.session_state.otp_verified = False
                        st.session_state.otp = None
                        st.session_state.user_email = ""
                        st.session_state.signup_existing_user = False
                        st.rerun()





                if st.session_state.get("otp_verified", False):

                    st.divider()

                    st.markdown(
                        '<div class="verify-email-heading">'
                        'Create your account</div>',
                        unsafe_allow_html=True,
                    )

                    if st.session_state.get(
                        "signup_existing_user", False
                    ):
                        st.info(
                            "This email already has a MedPredict "
                            "account. Create a username and password "
                            "to use for future logins. Your existing "
                            "health data will remain connected to your account."
                        )

                    name = st.text_input(
                        "Name",
                        placeholder="Your name",
                        key="signup_name",
                    )

                    username = st.text_input(
                        "Username",
                        placeholder="Choose a username",
                        key="signup_username",
                    )

                    password = st.text_input(
                        "Password",
                        placeholder="Create a password",
                        type="password",
                        key="signup_password",
                    )

                    confirm_password = st.text_input(
                        "Confirm Password",
                        placeholder="Re-enter your password",
                        type="password",
                        key="signup_confirm_password",
                    )

                    if st.button(
                        "Create Account  →",
                        type="primary",
                        width="stretch",
                        key="create_account_button",
                    ):

                        username = username.strip().lower()

                        if not username:
                            st.error("Please choose a username.")

                        elif len(username) < 3:
                            st.error(
                                "Username must be at least 3 characters."
                            )

                        elif not password:
                            st.error("Please create a password.")

                        elif len(password) < 8:
                            st.error(
                                "Password must be at least 8 characters."
                            )

                        elif password != confirm_password:
                            st.error(
                                "Passwords do not match."
                            )

                        else:
                            email = st.session_state.user_email
                            existing_user = get_user_by_email(email)

                            try:
                                if existing_user is None:
                                    user_id = create_account(
                                        email=email,
                                        username=username,
                                        password=password,
                                        name=name.strip() or None,
                                    )
                                else:
                                    user_id = existing_user[0]
                                    set_user_credentials(
                                        user_id=user_id,
                                        username=username,
                                        password=password,
                                    )


                                    if name.strip():
                                        conn = get_connection()
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            "UPDATE users SET name = ? WHERE id = ?",
                                            (name.strip(), user_id),
                                        )
                                        conn.commit()
                                        conn.close()



                                st.session_state.user_id = user_id
                                st.session_state.user_email = email
                                st.session_state.is_logged_in = True
                                st.session_state.verified = True
                                st.session_state.otp_verified = False
                                st.session_state.otp_sent = False
                                st.session_state.otp = None
                                st.session_state.signup_existing_user = False

                                st.success(
                                    "Account created successfully! 🎉"
                                )
                                st.rerun()

                            except ValueError as e:
                                st.error(str(e))
                            except Exception as e:
                                print(
                                    "Error creating account:",
                                    e
                                )
                                st.error(
                                    "Unable to create the account. "
                                    "Please try again."
                                )





            st.markdown(
                '<div class="mp-auth-foot">Educational and research use only. '
                'Model outputs are not medical diagnoses.</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    st.set_page_config(
        page_title="MedPredict | Sign in",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    login_page()
