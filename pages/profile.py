from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from database import (
    get_user_profile,
    update_user_name,
)

from auth import set_user_credentials
from database import get_connection
from werkzeug.security import check_password_hash
from utils import apply_custom_css






def verify_current_password(username, password):
    """Verify the stored password directly from the users table."""
    username = (username or "").strip().lower()
    password = password or ""

    if not username or not password:
        return False

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT password_hash
            FROM users
            WHERE LOWER(username) = ?
            """,
            (username,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None or not row[0]:
        return False

    stored_hash = row[0]


    try:
        if check_password_hash(stored_hash, password):
            return True
    except (ValueError, TypeError):
        pass


    if stored_hash.startswith("pbkdf2_sha256$"):
        import hashlib
        import hmac

        try:
            algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False

            expected = bytes.fromhex(digest_hex)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    return False






st.set_page_config(
    page_title="My Profile | HealthGuard AI",
    page_icon="👤",
    layout="wide",
)


from sidebar_compat import show_sidebar
show_sidebar()






if "healthai_theme" not in st.session_state:
    st.session_state.healthai_theme = "light"

apply_custom_css()
st.html('<div class="healthai-current-page-profile"></div>')






st.markdown(
    """
    <style>
        .profile-header {
            color: #12385f !important;
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 5px;
        }

        .profile-subtitle {
            color: #6a8097 !important;
            font-size: 16px;
            margin-bottom: 25px;
        }

        .profile-avatar {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: linear-gradient(135deg, #13b7b5, #168fe1);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white !important;
            font-size: 48px;
            margin-bottom: 15px;
        }

        .profile-name {
            color: #12385f !important;
            font-size: 25px;
            font-weight: 800;
        }

        .profile-username {
            color: #6a8097 !important;
            font-size: 15px;
            margin-top: 3px;
        }

        .profile-label {
            color: #6a8097 !important;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .profile-value {
            color: #173c59 !important;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 18px;
        }

        .edit-title {
            color: #12385f !important;
            font-size: 22px;
            font-weight: 800;
            margin-bottom: 15px;
        }

        [data-testid="stTextInput"] label {
            color: #29445c !important;
            font-weight: 600 !important;
        }

        [data-testid="stTextInput"] input {
            background: #ffffff !important;
            color: #173c59 !important;
            border: 1px solid #cfe0e9 !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
            color: #173c59 !important;
        }

        [data-testid="stCaptionContainer"] {
            color: #6a8097 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)






if not st.session_state.get("is_logged_in", False):
    st.warning("Please log in to access your profile.")
    st.stop()






user_id = st.session_state.get("user_id")

if user_id is None:
    st.error("Unable to identify the logged-in user.")
    st.stop()


user = get_user_profile(user_id)

if user is None:
    st.error("User profile could not be found.")
    st.stop()






user_id = user[0]
email = user[1]
name = user[2]
username = user[3]
created_at = user[4]

try:
    account_created_utc = datetime.fromisoformat(str(created_at))
    if account_created_utc.tzinfo is None:
        account_created_utc = account_created_utc.replace(tzinfo=timezone.utc)
    created_at_display = account_created_utc.astimezone(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d %B %Y, %I:%M:%S %p")
except Exception:
    created_at_display = str(created_at)







st.html('<div class="profile-header">My Profile 👤</div>')

st.html(
    '<div class="profile-subtitle">'
    'Manage and view your HealthGuard AI account information.'
    '</div>'
)






with st.container(border=True):

    left, right = st.columns(
        [0.35, 0.65],
        gap="large",
    )





    with left:

        st.html('<div class="profile-avatar">👤</div>')

        display_name = name if name else "HealthGuard User"

        st.html(f'<div class="profile-name">{display_name}</div>')

        if username:
            st.html(
                f'<div class="profile-username">@{username}</div>'
            )





    with right:

        st.html('<div class="profile-label">Username</div>')

        st.html(
            f'<div class="profile-value">'
            f'{username if username else "Not set"}'
            f'</div>'
        )

        st.html('<div class="profile-label">Email Address</div>')

        st.html(f'<div class="profile-value">{email}</div>')

        st.html('<div class="profile-label">Name</div>')

        st.html(
            f'<div class="profile-value">'
            f'{name if name else "Not set"}'
            f'</div>'
        )

        st.html('<div class="profile-label">Account Created</div>')

        st.html(f'<div class="profile-value">{created_at_display}</div>')






st.write("")

st.subheader("Account Information")

info1, info2, info3 = st.columns(3)

with info1:

    st.metric(
        "Account Status",
        "Active",
    )

with info2:

    st.metric(
        "Email Verified",
        "Yes",
    )

with info3:

    st.metric(
        "Authentication",
        "Password",
    )






st.write("")

with st.container(border=True):

    st.html('<div class="edit-title">Edit Profile ✏️</div>')

    edited_name = st.text_input(
        "Name",
        value=name or "",
        placeholder="Enter your name",
        key="edit_profile_name",
    )

    edited_username = st.text_input(
        "Username",
        value=username or "",
        placeholder="Enter your username",
        key="edit_profile_username",
    )

    st.write("")

    st.markdown(
        "**Change Password**",
    )

    st.caption(
        "Leave the new password fields empty if you do not "
        "want to change your password."
    )

    current_password = st.text_input(
        "Current Password",
        type="password",
        placeholder="Enter your current password",
        key="edit_current_password",
    )

    new_password = st.text_input(
        "New Password",
        type="password",
        placeholder="Enter new password",
        key="edit_new_password",
    )

    confirm_password = st.text_input(
        "Confirm New Password",
        type="password",
        placeholder="Confirm new password",
        key="edit_confirm_password",
    )

    if st.button(
        "Save Changes",
        type="primary",
        width="stretch",
        key="save_profile_changes",
    ):





        edited_name = edited_name.strip()
        edited_username = edited_username.strip().lower()

        if not edited_username:

            st.error(
                "Username cannot be empty."
            )

        else:

            username_changed = (
                edited_username != (username or "").lower()
            )

            password_changed = bool(
                new_password or confirm_password
            )





            if password_changed:

                if not current_password:

                    st.error(
                        "Enter your current password to "
                        "change your password."
                    )

                elif not new_password:

                    st.error(
                        "Please enter a new password."
                    )

                elif new_password != confirm_password:

                    st.error(
                        "New passwords do not match."
                    )

                elif len(new_password) < 6:

                    st.error(
                        "New password must be at least 6 characters."
                    )

                else:

                    password_valid = verify_current_password(
                        username,
                        current_password
                    )

                    if not password_valid:

                        st.error(
                            "Current password is incorrect."
                        )

                    else:





                        update_user_name(
                            user_id,
                            edited_name
                        )





                        try:

                            set_user_credentials(
                                user_id,
                                edited_username,
                                new_password
                            )

                            st.success(
                                "Profile updated successfully! 🎉"
                            )

                            st.rerun()

                        except ValueError as e:

                            st.error(str(e))





            elif username_changed:

                if not current_password:

                    st.error(
                        "Enter your current password to "
                        "change your username."
                    )

                else:

                    password_valid = verify_current_password(
                        username,
                        current_password
                    )

                    if not password_valid:

                        st.error(
                            "Current password is incorrect."
                        )

                    else:

                        try:


                            conn = get_connection()
                            try:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT password_hash FROM users WHERE id = ?",
                                    (user_id,),
                                )
                                hash_row = cursor.fetchone()
                            finally:
                                conn.close()

                            if not hash_row or not hash_row[0]:
                                st.error(
                                    "Your account does not have a valid password set."
                                )
                                st.stop()

                            existing_password_hash = hash_row[0]

                            update_user_name(
                                user_id,
                                edited_name
                            )

                            from database import update_user_credentials

                            update_user_credentials(
                                user_id,
                                edited_username,
                                existing_password_hash
                            )

                            st.success(
                                "Profile updated successfully! 🎉"
                            )

                            st.rerun()

                        except ValueError as e:

                            st.error(str(e))





            else:

                update_user_name(
                    user_id,
                    edited_name
                )

                st.success(
                    "Profile updated successfully! 🎉"
                )

                st.rerun()






st.write("")

if st.button(
    "Logout",
    type="secondary",
    width="stretch",
    key="profile_logout",
):

    st.session_state["is_logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["user_email"] = ""
    st.session_state["verified"] = False
    st.session_state["otp"] = None
    st.session_state["otp_sent"] = False

    st.switch_page("app.py")