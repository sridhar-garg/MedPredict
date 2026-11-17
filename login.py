import re
from pathlib import Path

import streamlit as st

from database import get_connection
from utils import apply_custom_css

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






def login_page():

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
        if key not in st.session_state:
            st.session_state[key] = value





    apply_custom_css()

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        #MainMenu, footer { visibility: hidden !important; }

        .block-container,
        [data-testid="stMainBlockContainer"] {
            max-width: 1120px !important;
            padding-top: 56px !important;
            padding-bottom: 40px !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            border: 1px solid var(--line) !important;
            border-radius: var(--radius-panel) !important;
            box-shadow: none !important;
            padding: 12px 8px !important;
        }

        .lg-brand {
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 56px;
            font-family: var(--serif); font-size: 26px; font-weight: 600;
            color: var(--ink);
        }
        .lg-brand svg { width: 32px; height: 32px; }
        .lg-title {
            margin: 0 0 16px !important;
            font-family: var(--serif) !important;
            font-size: clamp(2rem, 3.6vw, 2.9rem) !important;
            line-height: 1.12 !important; font-weight: 600 !important;
            letter-spacing: -0.02em; color: var(--ink) !important;
        }
        .lg-lead {
            max-width: 46ch; margin: 0 0 36px !important;
            font-size: 1.1rem !important; line-height: 1.6 !important;
            color: var(--ink-2) !important;
        }
        .lg-points { list-style: none; margin: 0; padding: 0; max-width: 46ch; }
        .lg-points li {
            padding: 16px 0; border-top: 1px solid var(--line);
        }
        .lg-points b { display: block; color: var(--ink); font-size: 15px; font-weight: 600; }
        .lg-points span { display: block; margin-top: 2px; color: var(--muted); font-size: 14.5px; }
        .lg-foot { margin-top: 32px; color: var(--muted); font-size: 13px; }

        .login-heading {
            margin: 4px 0 6px; color: var(--ink);
            font-family: var(--serif); font-size: 28px; font-weight: 600;
            letter-spacing: -0.01em;
        }
        .login-description { margin-bottom: 20px; color: var(--muted); font-size: 15px; line-height: 1.55; }
        .verify-email-heading {
            margin: 12px 0 14px; color: var(--ink);
            font-family: var(--serif); font-size: 22px; font-weight: 600;
        }

        div[data-testid="stTextInput"] input { height: 46px !important; padding: 0 14px !important; }
        div[data-testid="stTextInput"] label p { color: var(--ink) !important; font-size: 14.5px !important; font-weight: 500 !important; }

        div[data-testid="stRadio"] [role="radiogroup"] { gap: 20px !important; }
        div[data-testid="stRadio"] label p,
        div[data-testid="stRadio"] label span { color: var(--ink) !important; opacity: 1 !important; font-size: 15px !important; }

        @media (max-width: 900px) {
            .lg-brand { margin-bottom: 28px; }
            .lg-lead { margin-bottom: 20px !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown(
            "\n".join([
                '<div class="lg-brand">',
                '<svg viewBox="0 0 24 24" aria-hidden="true"><rect width="24" height="24" rx="6" fill="#0E5E6F"/>'
                '<path d="M12 6.5v11M6.5 12h11" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>',
                'HealthAI</div>',
                '<h1 class="lg-title">Health risk assessment you can understand</h1>',
                '<p class="lg-lead">Estimate your risk of diabetes, heart disease or breast cancer, '
                'and see which inputs drove each result.</p>',
                '<ul class="lg-points">',
                '<li><b>Five models, compared</b><span>Each model gives its own estimate, '
                'and the results are combined into one overall figure.</span></li>',
                '<li><b>Results that explain themselves</b><span>SHAP and feature importance show '
                'what pushed a result up or down.</span></li>',
                '<li><b>Your history in one place</b><span>Past assessments are saved to your '
                'account so you can review them.</span></li>',
                '</ul>',
                '<p class="lg-foot">Research prototype for educational use. '
                'Not a medical diagnosis.</p>',
            ]),
            unsafe_allow_html=True,
        )

    with right:

        with st.container(border=True):

            st.markdown(
                '<div class="login-heading">Welcome to HealthAI</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="login-description">'
                'Log in with your username and password, '
                'or create an account.'
                '</div>',
                unsafe_allow_html=True,
            )

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
                    "Log in",
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

                            st.success("Login successful.")
                            st.rerun()





            else:





                if not st.session_state.get("otp_sent", False):

                    email = st.text_input(
                        "Email Address",
                        placeholder="you@example.com",
                        key="signup_email",
                    )

                    if st.button(
                        "Send OTP",
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
                        f"Verification code sent to "
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
                                    "Email verified."
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
                        "Use a different email",
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
                            "This email already has a HealthAI "
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
                        "Create account",
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
                                    "Account created."
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








if __name__ == "__main__":

    st.set_page_config(
        page_title="HealthAI",
        page_icon=str(Path(__file__).resolve().parent / "assets" / "favicon.png"),
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    login_page()