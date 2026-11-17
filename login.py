import re

import streamlit as st

from database import get_connection
from auth import (
    generate_otp, send_email_otp, get_user_by_email, create_account,
    authenticate_user, set_user_credentials,
)
from ui import apply_theme, brand, html, icon, studio_image, theme_switch


def is_valid_email(email: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}$"
    return re.fullmatch(pattern, email) is not None


def login_page():
    defaults = {
        "otp_sent": False, "verified": False, "user_email": "", "otp": None,
        "user_id": None, "is_logged_in": False, "auth_mode": "Login",
        "otp_verified": False, "signup_existing_user": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    top_left, top_right = st.columns([4, 1], vertical_alignment="center")
    with top_left:
        html('<div class="mp-auth-top">' + brand() + '</div>')
    with top_right:
        theme_switch()
    apply_theme()
    html('<span class="mp-auth-marker" aria-hidden="true"></span>')

    left, right = st.columns([1.08, 1], gap="large")
    with left:
        html(f'''<section class="mp-auth-visual" aria-label="About MedPredict">
        <img src="{studio_image()}" alt="Silver stethoscope on a deep violet studio surface">
        <div><span class="mp-auth-pill">{icon("spark", 13)} A little insight. A healthier tomorrow.</span></div>
        <div class="mp-auth-copy">
        <h1>Your health.<br>A clearer <span class="mp-heading-accent">perspective.</span></h1>
        <p>Explore your health with explainable AI, thoughtful assessments, and insights you can understand.</p>
        <div class="mp-auth-features">
        <div><b>3 assessments</b><small>One connected workspace</small></div>
        <div><b>Explainable AI</b><small>Understand the factors</small></div>
        <div><b>Made for you</b><small>Your history, together</small></div>
        </div><div class="mp-auth-copyright">MedPredict · Research &amp; education</div>
        </div></section>''')

    with right:
        with st.container(border=True):
            html('''<span class="mp-auth-form-marker" aria-hidden="true"></span>
            <span class="mp-eyebrow">WELCOME TO MEDPREDICT</span>
            <h2 class="mp-auth-heading">Your next step starts here.</h2>
            <p class="mp-auth-description">Sign in to your personal health workspace,<br>or create an account to get started.</p>''')
            auth_mode = st.radio(
                "Choose an option",
                ["Login", "Create Account"],
                horizontal=True,
                key="auth_mode",
                width="stretch",
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


            html('<p class="mp-auth-small">' + icon("shield", 12) +
                 ' Your account keeps your assessments together.<br>'
                 'An educational prototype. Not a medical diagnosis.</p>')
