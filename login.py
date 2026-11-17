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





    st.markdown(
        """
        <style>

        /* ====================================================
           STREAMLIT CLEANUP
        ==================================================== */

        [data-testid="stSidebar"] {
            display: none !important;
        }
        .verify-email-heading {
    color: #12385f !important;
    font-size: 24px !important;
    font-weight: 800 !important;
    line-height: 1.3 !important;
    margin: 12px 0 16px 0 !important;
    opacity: 1 !important;
}
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        #MainMenu,
        header,
        footer {
            visibility: hidden !important;
            height: 0 !important;
        }
        
        /* ====================================================
           PAGE BACKGROUND
        ==================================================== */

        .stApp {
            background:
                radial-gradient(
                    circle at 10% 15%,
                    rgba(174, 239, 232, 0.55),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 90% 20%,
                    rgba(181, 207, 255, 0.55),
                    transparent 35%
                ),
                linear-gradient(
                    135deg,
                    #eefbf9 0%,
                    #f7fbff 48%,
                    #edf4ff 100%
                );

            min-height: 100vh;
        }


        /* ====================================================
           MAIN CONTAINER
        ==================================================== */

        .block-container {
            max-width: 1500px !important;
            padding-top: 28px !important;
            padding-bottom: 20px !important;
            padding-left: 30px !important;
            padding-right: 30px !important;
        }


        /* ====================================================
           REMOVE COLUMN BACKGROUNDS
        ==================================================== */

        [data-testid="column"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            min-height: 0 !important;
        }


        /* ====================================================
           BRAND
        ==================================================== */

        .brand-title {
            color: #123b67;
            font-size: 36px;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: -1.2px;
        }

        .brand-title span {
            color: #16b5b1;
        }

        .brand-subtitle {
            color: #5f7891;
            font-size: 16px;
            font-weight: 500;
            margin-top: 6px;
        }


        /* ====================================================
           HERO IMAGE
        ==================================================== */

        .hero-image-wrap {
            width: 100%;
            overflow: hidden;
            border-radius: 18px;
            border: none;
            box-shadow: none;
            background: transparent;
        }

        .hero-image-wrap img {
            display: block;
            width: 100%;
            border-radius: 18px;
        }


        /* ====================================================
           STREAMLIT CARDS
        ==================================================== */

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.90) !important;
            border: 1px solid #d8e5ee !important;
            border-radius: 20px !important;
            box-shadow: 0 12px 34px rgba(45, 91, 117, 0.08) !important;
        }


        /* ====================================================
           FEATURE CARD
        ==================================================== */

        .feature-icon {
            font-size: 28px;
            text-align: center;
            margin-bottom: 7px;
        }

        .feature-title {
            color: #12365f;
            font-size: 18px;
            font-weight: 800;
            line-height: 1.2;
            text-align: center;
        }

        .feature-description {
            color: #637b91;
            font-size: 14px;
            line-height: 1.55;
            text-align: center;
            margin-top: 7px;
        }


        /* ====================================================
           LOGIN LOGO
        ==================================================== */

        .login-logo {
            width: 84px;
            height: 84px;
            margin: 4px auto 24px auto;
            border-radius: 50%;
            background: #ffffff;
            border: 1px solid #d8edf2;

            box-shadow:
                0 0 0 11px rgba(228, 250, 250, 0.72),
                0 10px 28px rgba(34, 174, 190, 0.12);

            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 43px;
        }


        /* ====================================================
           LOGIN HEADING
        ==================================================== */

        .login-heading {
            color: #12385f;
            font-size: 32px;
            line-height: 1.2;
            font-weight: 800;
            letter-spacing: -0.5px;
            text-align: center;
            margin-bottom: 8px;
        }

        .login-description {
            color: #6a8097;
            font-size: 15px;
            line-height: 1.65;
            text-align: center;
            margin-bottom: 25px;
        }


        /* ====================================================
           INPUT
        ==================================================== */

        div[data-testid="stTextInput"] {
            margin-bottom: 9px;
        }

        div[data-testid="stTextInput"] label {
            color: #234c6b !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }

        div[data-testid="stTextInput"] input {
            height: 50px !important;
            min-height: 50px !important;
            padding: 0 15px !important;
            background: #ffffff !important;
            color: #173c59 !important;
            border: 1px solid #c9d9e5 !important;
            border-radius: 11px !important;
            font-size: 15px !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #27b5c3 !important;
            box-shadow: 0 0 0 3px rgba(39, 181, 195, 0.12) !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #93a7ba !important;
            opacity: 1 !important;
        }


        /* ====================================================
           BUTTON
        ==================================================== */

        div.stButton > button {
            width: 100%;
            min-height: 50px !important;
            border: none !important;
            border-radius: 11px !important;
            font-size: 15px !important;
            font-weight: 750 !important;
            color: white !important;

            background: linear-gradient(
                90deg,
                #13b7b5 0%,
                #168fe1 100%
            ) !important;

            box-shadow:
                0 10px 22px rgba(21, 154, 203, 0.18) !important;
        }

        div.stButton > button:hover {
            transform: translateY(-1px);

            box-shadow:
                0 13px 28px rgba(21, 154, 203, 0.24) !important;
        }


        /* ====================================================
           WHY HEALTHGUARD
        ==================================================== */

        .why-title {
            color: #173b60;
            font-size: 17px;
            font-weight: 800;
            line-height: 1.25;
        }

        .why-description {
            color: #6d8398;
            font-size: 14px;
            line-height: 1.45;
            margin-top: 4px;
        }

        .why-icon {
            font-size: 25px;
            line-height: 1;
        }


        /* ====================================================
           FOOTER
        ==================================================== */

        .footer-text {
            color: #70869d;
            font-size: 13px;
            text-align: center;
            margin-top: 18px;
        }


        /* ====================================================
           MOBILE
        ==================================================== */

        @media (max-width: 900px) {

            .block-container {
                padding-left: 18px !important;
                padding-right: 18px !important;
            }

            .brand-title {
                font-size: 30px;
            }

            .login-heading {
                font-size: 28px;
            }
        }


        /* ====================================================
           LOGIN METHOD RADIO — HIGH VISIBILITY
        ==================================================== */

        /* Make "Choose how you want to sign in" clearly visible */
        div[data-testid="stRadio"] > label p,
        div[data-testid="stRadio"] > label {
            color: #173b60 !important;
            opacity: 1 !important;
            font-size: 14px !important;
            font-weight: 700 !important;
        }

        /* Make Email / Mobile Number text clearly visible */
        div[data-testid="stRadio"] [role="radiogroup"] label,
        div[data-testid="stRadio"] [role="radiogroup"] label p,
        div[data-testid="stRadio"] [role="radiogroup"] span,
        div[data-testid="stRadio"] [data-baseweb="radio"] label,
        div[data-testid="stRadio"] [data-baseweb="radio"] label p {
            color: #173b60 !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-size: 14px !important;
            font-weight: 700 !important;
        }

        /* Give each login option a clean, visible area */
        div[data-testid="stRadio"] [role="radiogroup"] {
            gap: 18px !important;
            margin-top: 4px !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > label {
            color: #173b60 !important;
            opacity: 1 !important;
        }

        /* Radio circles */
        div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
            border-color: #5c7892 !important;
            opacity: 1 !important;
        }

        /* Selected radio circle */
        div[data-testid="stRadio"] [data-baseweb="radio"][aria-checked="true"] > div:first-child {
            border-color: #168fe1 !important;
        }

        /* Prevent Streamlit/theme opacity from fading the options */
        div[data-testid="stRadio"] *,
        div[data-testid="stRadio"] label * {
            opacity: 1 !important;
        }

        /* Slightly separate the login method selector from the input */
        div[data-testid="stRadio"] {
            margin-top: 4px !important;
            margin-bottom: 18px !important;
        }

        /* ====================================================
           LOGIN METHOD — EXTRA HIGH VISIBILITY
        ==================================================== */
        div[data-testid="stRadio"] {
            background: rgba(255, 255, 255, 0.96) !important;
            border: 1px solid #c7dce8 !important;
            border-radius: 14px !important;
            padding: 12px 16px 14px 16px !important;
            box-shadow: 0 5px 16px rgba(35, 91, 120, 0.08) !important;
        }

        div[data-testid="stRadio"] > label {
            color: #12385f !important;
            -webkit-text-fill-color: #12385f !important;
            opacity: 1 !important;
            font-size: 15px !important;
            font-weight: 800 !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > label {
            background: #f4f9fc !important;
            border: 1px solid #d4e3ec !important;
            border-radius: 10px !important;
            padding: 9px 14px !important;
            min-height: 42px !important;
            color: #12385f !important;
            -webkit-text-fill-color: #12385f !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > label p,
        div[data-testid="stRadio"] [role="radiogroup"] > label span {
            color: #12385f !important;
            -webkit-text-fill-color: #12385f !important;
            opacity: 1 !important;
            font-weight: 750 !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
            background: #eaf7f8 !important;
            border-color: #6cc6ce !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )






    left, right = st.columns(
        [1.03, 0.97],
        gap="large",
    )






    with left:

        brand_icon_col, brand_text_col = st.columns(
            [0.11, 0.89],
            vertical_alignment="center",
        )

        with brand_icon_col:

            st.markdown(
                """
                <div style="
                    width:62px;
                    height:62px;
                    border-radius:18px;
                    background:rgba(255,255,255,.90);
                    border:1px solid #d0e3ed;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:34px;
                    box-shadow:0 10px 28px rgba(47,119,145,.10);
                ">
                    🛡️
                </div>
                """,
                unsafe_allow_html=True,
            )

        with brand_text_col:

            st.markdown(
                """
                <div class="brand-title">
                    HealthGuard <span>AI</span>
                </div>

                <div class="brand-subtitle">
                    AI-powered health risk prediction &amp; monitoring
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='height:24px'></div>",
            unsafe_allow_html=True,
        )






        image_path = (
            Path(__file__).resolve().parent
            / "assets"
            / "healthguard_hero.png"
        )

        if image_path.exists():

            st.markdown(
                '<div class="hero-image-wrap">',
                unsafe_allow_html=True,
            )

            st.image(
                str(image_path),
                width="stretch",
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        else:

            st.warning(
                "Hero image not found. "
                "Put healthguard_hero.png inside the assets folder."
            )


        st.markdown(
            "<div style='height:20px'></div>",
            unsafe_allow_html=True,
        )






        with st.container(border=True):

            c1, c2, c3 = st.columns(
                3,
                gap="medium",
            )

            with c1:

                st.markdown(
                    '<div class="feature-icon">🧠</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="feature-title">'
                    'AI-Powered<br>Prediction'
                    '</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="feature-description">'
                    'Advanced machine learning for accurate risk prediction'
                    '</div>',
                    unsafe_allow_html=True,
                )

            with c2:

                st.markdown(
                    '<div class="feature-icon">🔐</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="feature-title">'
                    'Secure &amp;<br>Private'
                    '</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="feature-description">'
                    'Your health data is encrypted and fully protected'
                    '</div>',
                    unsafe_allow_html=True,
                )

            with c3:

                st.markdown(
                    '<div class="feature-icon">📊</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="feature-title">'
                    'Smart<br>Insights'
                    '</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<div class="feature-description">'
                    'Personalized insights to help you live a healthier life'
                    '</div>',
                    unsafe_allow_html=True,
                )


        st.markdown(
            '<div class="footer-text">'
            '© 2026 HealthGuard AI. All rights reserved.'
            '</div>',
            unsafe_allow_html=True,
        )






    with right:

        with st.container(border=True):





            st.markdown(
                '<div class="login-logo">🩺</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="login-heading">'
                'Welcome back! 👋'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="login-description">'
                'Log in with your username and password<br>'
                'or create your HealthGuard AI account.'
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
                            "This email already has a HealthGuard AI "
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





            st.divider()

            st.markdown(
                "<h3 style='text-align:center;"
                "color:#173b60;"
                "font-size:17px;"
                "margin:0 0 12px 0;'>"
                "Why HealthGuard AI?</h3>",
                unsafe_allow_html=True,
            )

            why_items = [
                (
                    "🧠",
                    "AI-Powered Prediction",
                    "Intelligent health risk analysis",
                ),
                (
                    "📊",
                    "Personalized Monitoring",
                    "Track your health insights in real-time",
                ),
                (
                    "🔐",
                    "Secure Access",
                    "Secure username and password login",
                ),
            ]

            for index, (
                icon,
                title,
                description,
            ) in enumerate(why_items):

                icon_col, text_col = st.columns(
                    [0.13, 0.87],
                    vertical_alignment="center",
                )

                with icon_col:

                    st.markdown(
                        f'<div class="why-icon">{icon}</div>',
                        unsafe_allow_html=True,
                    )

                with text_col:

                    st.markdown(
                        f'<div class="why-title">'
                        f'{title}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<div class="why-description">'
                        f'{description}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if index < len(why_items) - 1:

                    st.markdown(
                        "<hr style='border:none;"
                        "border-top:1px solid #e5edf2;"
                        "margin:10px 0 2px 0;'>",
                        unsafe_allow_html=True,
                    )

            st.markdown(
                "<div style='text-align:center;"
                "color:#71869a;"
                "font-size:12.5px;"
                "margin-top:20px;'>"
                "🔒 <b>Secure OTP verification</b>"
                "&nbsp; • &nbsp;"
                "Your health data stays protected"
                "</div>",
                unsafe_allow_html=True,
            )






if __name__ == "__main__":

    st.set_page_config(
        page_title="HealthGuard AI",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    login_page()