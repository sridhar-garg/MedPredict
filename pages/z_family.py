import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

from database import (
    get_connection,
    initialize_database,
    find_family_user,
    add_family_connection,
    get_pending_family_requests,
    get_family_connections,
    accept_family_connection,
    decline_family_connection,
    revoke_family_connection,
    get_family_assessments,
    get_user_profile,
)
from utils import apply_custom_css, page_intro
from auth import (send_family_request_email, send_family_acceptance_email, send_family_request_email_with_buttons)








load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


def send_family_email_direct(receiver_email, subject, body):
    """
    Send a Family email using the SAME Gmail SMTP credentials already
    used by the working OTP system.
    Returns (success, diagnostic_message).
    """
    sender_email = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email:
        return False, "GMAIL_ADDRESS was not found in the project's .env file."

    if not app_password:
        return False, "GMAIL_APP_PASSWORD was not found in the project's .env file."

    receiver_email = (receiver_email or "").strip().lower()
    if not receiver_email:
        return False, "The recipient email address is empty."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(sender_email, app_password)
            refused = smtp.sendmail(
                sender_email,
                [receiver_email],
                message.as_string(),
            )

        if refused:
            return False, f"Gmail refused the recipient: {refused}"

        return True, f"Gmail accepted the email for {receiver_email}."

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def send_family_request_email_direct(receiver_email, sender_name, sender_username, relationship):
    display_sender = sender_name or sender_username or "A MedPredict user"
    body = f"""Hello,

You have received a new family connection request on MedPredict.

From: {display_sender}
Username: @{sender_username or "user"}
Relationship: {relationship}

Please log in to MedPredict and open Family Health to accept or decline this request.

Your health information will remain private until the request is accepted.

If you did not expect this request, you can simply decline it from the Family Health page.

Regards,
MedPredict
"""
    return send_family_email_direct(
        receiver_email,
        "MedPredict - New Family Connection Request",
        body,
    )


def send_family_acceptance_email_direct(receiver_email, accepter_name, accepter_username, relationship):
    display_accepter = accepter_name or accepter_username or "Your family member"
    body = f"""Hello,

Your MedPredict family connection request has been accepted.

Family member: {display_accepter}
Username: @{accepter_username or "user"}
Relationship: {relationship}

You can now open Family Health in MedPredict to view your accepted family connection.

Regards,
MedPredict
"""
    return send_family_email_direct(
        receiver_email,
        "MedPredict - Family Connection Accepted",
        body,
    )






st.set_page_config(
    page_title="Family Health | MedPredict",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
)


from sidebar_compat import show_sidebar
show_sidebar()






if not st.session_state.get("is_logged_in", False):
    st.warning("Please log in to access Family Health.")
    st.stop()

user_id = st.session_state.get("user_id")

if user_id is None:
    st.error("Unable to identify the logged-in user.")
    st.stop()




initialize_database()
apply_custom_css()













page_intro("Family health connections", "Connect with registered family members and view shared assessments only after permission is granted.", "◎", "YOUR ACCOUNT / FAMILY")


accept_notice = st.session_state.pop("family_accept_notice", None)
if accept_notice:
    if "could not be sent" in accept_notice:
        st.warning(accept_notice)
    else:
        st.success(accept_notice)






connect_tab, pending_tab, family_tab = st.tabs(["Send connection request", "Pending requests", "Connected family"])

with connect_tab:
    st.markdown(
        """
        <div class="family-card">
            <h3>➕ Add Family Member</h3>
            <p>
                Send a connection request using a registered username or email.
                Health information is never shared before the request is accepted.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    with st.form("family_add_form", clear_on_submit=True):
        search_col, relation_col, send_col = st.columns(
            [2.7, 1.5, 0.9],
            vertical_alignment="bottom"
        )

        with search_col:
            identifier = st.text_input(
                "Username or email",
                placeholder="Enter registered username or email"
            )

        with relation_col:
            relationship = st.selectbox(
                "Relationship",
                [
                    "Mother",
                    "Father",
                    "Sister",
                    "Brother",
                    "Spouse",
                    "Son",
                    "Daughter",
                    "Other",
                ]
            )

        with send_col:
            send_request = st.form_submit_button(
                "Send Request",
                type="primary",
                use_container_width=True
            )

    if send_request:
        if not identifier.strip():
            st.error("Please enter a registered username or email.")
        else:
            target = find_family_user(identifier, user_id)

            if target is None:
                st.error("No other registered user was found with that username or email.")
            else:
                target_id = target[0]
                target_name = target[2] or target[3] or target[1]

                success, message = add_family_connection(
                    user_id,
                    target_id,
                    relationship
                )

                if success:


                    sender = get_user_profile(user_id)

                    if sender is not None:
                        sender_name = sender[2]
                        sender_username = sender[3]
                    else:
                        sender_name = None
                        sender_username = None

                    recipient_email = (target[1] or "").strip().lower()

                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM family_connections WHERE owner_user_id=? AND member_user_id=? AND status='pending' LIMIT 1", (user_id, target_id))
                    created_row = cursor.fetchone()
                    conn.close()
                    if created_row:
                        email_sent, email_detail = send_family_request_email_with_buttons(
                            recipient_email, sender_name, sender_username, relationship, created_row[0], target_id
                        )
                    else:
                        email_sent, email_detail = False, "The new family request could not be located."

                    if email_sent:
                        st.success(
                            f"Family request sent to {target_name}."
                        )
                        st.info(f"📧 {email_detail}")
                    else:
                        st.warning(
                            f"Family request was created for {target_name}, "
                            f"but the notification email could not be sent."
                        )
                        st.error(f"📧 Email error: {email_detail}")
                else:
                    st.warning(message)



                    if "already pending" in str(message).lower():
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            SELECT
                                fc.id,
                                fc.relationship,
                                u.email
                            FROM family_connections fc
                            JOIN users u ON u.id = fc.member_user_id
                            WHERE fc.owner_user_id = ?
                              AND fc.member_user_id = ?
                              AND fc.status = 'pending'
                            LIMIT 1
                            """,
                            (user_id, target_id),
                        )
                        pending_row = cursor.fetchone()
                        conn.close()

                        if pending_row:
                            sender = get_user_profile(user_id)

                            sender_name = sender[2] if sender is not None else None
                            sender_username = sender[3] if sender is not None else None

                            pending_relationship = pending_row[1] or relationship
                            pending_email = (pending_row[2] or "").strip().lower()

                            email_sent, email_detail = send_family_request_email_with_buttons(
                                pending_email, sender_name, sender_username, pending_relationship, pending_row[0], target_id
                            )

                            if email_sent:
                                st.success(
                                    f"📧 Family request email sent successfully to {pending_email}."
                                )
                                st.info(email_detail)
                            else:
                                st.error(
                                    f"❌ The pending request exists, but the email could not be sent."
                                )
                                st.error(f"📧 Email error: {email_detail}")

with pending_tab:
    pending_requests = get_pending_family_requests(user_id)

    st.markdown(
        '<div class="family-section-space"></div>',
        unsafe_allow_html=True
    )

    st.subheader("📩 Pending Requests")

    if not pending_requests:
        st.info("You have no pending family requests.")
    else:
        for request in pending_requests:
            (
                connection_id,
                sender_id,
                sender_name,
                sender_username,
                sender_email,
                requested_relationship,
                created_at,
            ) = request

            display_name = sender_name or sender_username or sender_email

            st.markdown(
                f"""
                <div class="family-request">
                    <div class="family-member-name">{display_name}</div>
                    <div class="family-member-meta">
                        @{sender_username or "user"} • {sender_email}
                    </div>
                    <span class="family-badge">
                        Requested as {requested_relationship}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            accept_col, decline_col, spacer = st.columns([1, 1, 4])

            with accept_col:
                if st.button(
                    "✓ Accept",
                    key=f"accept_{connection_id}",
                    type="primary",
                    use_container_width=True
                ):


                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT
                            u.email,
                            u.name,
                            u.username,
                            fc.relationship
                        FROM family_connections fc
                        JOIN users u ON u.id = fc.owner_user_id
                        WHERE fc.id = ?
                          AND fc.member_user_id = ?
                          AND fc.status = 'pending'
                        LIMIT 1
                        """,
                        (connection_id, user_id),
                    )
                    requester = cursor.fetchone()
                    conn.close()

                    if accept_family_connection(connection_id, user_id):
                        current_user = get_user_profile(user_id)

                        if current_user is not None:
                            accepter_name = current_user[2]
                            accepter_username = current_user[3]
                        else:
                            accepter_name = None
                            accepter_username = None

                        acceptance_email_sent = False

                        if requester is not None and requester[0]:
                            acceptance_email_sent, acceptance_email_detail = (
                                send_family_acceptance_email_direct(
                                    requester[0].strip().lower(),
                                    accepter_name,
                                    accepter_username,
                                    requester[3] or "Family Member",
                                )
                            )

                        if requester is not None and acceptance_email_sent:
                            st.session_state["family_accept_notice"] = (
                                f"✓ Family connection accepted. "
                                f"📧 {requester[0]} was notified by email."
                            )
                        elif requester is not None:
                            st.session_state["family_accept_notice"] = (
                                f"✓ Family connection accepted, but the email to "
                                f"{requester[0]} could not be sent. "
                                f"{acceptance_email_detail}"
                            )
                        else:
                            st.session_state["family_accept_notice"] = (
                                "✓ Family connection accepted."
                            )

                        st.rerun()
                    else:
                        st.error("This request is no longer available.")

            with decline_col:
                if st.button(
                    "Decline",
                    key=f"decline_{connection_id}",
                    use_container_width=True
                ):
                    if decline_family_connection(connection_id, user_id):
                        st.success("Request declined.")
                        st.rerun()
                    else:
                        st.error("This request is no longer available.")

with family_tab:
    connections = get_family_connections(user_id)

    st.markdown(
        '<div class="family-section-space"></div>',
        unsafe_allow_html=True
    )

    st.subheader("👨‍👩‍👧‍👦 My Family")

    if not connections:
        st.info(
            "No accepted family members yet. Use the connection-request tab to send an invitation to connect."
        )
    else:
        for connection in connections:
            (
                connection_id,
                other_user_id,
                other_name,
                other_username,
                other_email,
                relationship,
                created_at,
            ) = connection

            display_name = other_name or other_username or other_email

            st.markdown(
                f"""
                <div class="family-request">
                    <div class="family-member-name">{display_name}</div>
                    <div class="family-member-meta">
                        @{other_username or "user"} • {other_email}
                    </div>
                    <span class="family-badge">{relationship}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            view_col, remove_col, spacer = st.columns([1.35, 1, 3.65])

            with view_col:
                if st.button(
                    "View Health",
                    key=f"view_health_{connection_id}",
                    use_container_width=True
                ):
                    st.session_state["family_view_member_id"] = other_user_id
                    st.session_state["family_view_member_name"] = display_name
                    st.rerun()

            with remove_col:
                if st.button(
                    "Remove",
                    key=f"remove_family_{connection_id}",
                    use_container_width=True
                ):
                    if revoke_family_connection(connection_id, user_id):
                        if st.session_state.get("family_view_member_id") == other_user_id:
                            st.session_state.pop("family_view_member_id", None)
                            st.session_state.pop("family_view_member_name", None)
                        st.success("Family connection removed.")
                        st.rerun()
                    else:
                        st.error("Unable to remove this connection.")






    selected_member_id = st.session_state.get("family_view_member_id")
    selected_member_name = st.session_state.get("family_view_member_name")

    if selected_member_id is not None:
        st.markdown(
            '<div class="family-section-space"></div>',
            unsafe_allow_html=True
        )

        st.subheader(
            f"🩺 Health Assessments — {selected_member_name or 'Family Member'}"
        )



        assessments = get_family_assessments(user_id, selected_member_id)

        if not assessments:
            st.info("This family member has no saved health assessments yet.")
        else:
            for assessment in assessments:
                (
                    assessment_id,
                    disease,
                    input_data,
                    prediction,
                    probability,
                    evaluation,
                    created_at,
                ) = assessment

                try:
                    probability_text = (
                        f"{float(probability) * 100:.1f}%"
                        if probability is not None
                        else "N/A"
                    )
                except (TypeError, ValueError):
                    probability_text = str(probability)

                try:
                    utc_time = datetime.fromisoformat(str(created_at))
                    if utc_time.tzinfo is None:
                        utc_time = utc_time.replace(tzinfo=timezone.utc)
                    ist_time = utc_time.astimezone(ZoneInfo("Asia/Kolkata"))
                    date_text = ist_time.strftime("%d %B %Y, %I:%M:%S %p")
                except Exception:
                    date_text = str(created_at)

                st.markdown(
                    f"""
                    <div class="family-card">
                        <h3>{disease}</h3>
                        <p><b>Prediction:</b> {prediction}</p>
                        <p><b>Probability:</b> {probability_text}</p>
                        <p><b>Evaluation:</b> {evaluation}</p>
                        <p><b>Assessed:</b> {date_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )



                try:
                    parsed_inputs = json.loads(input_data) if input_data else {}
                except (TypeError, json.JSONDecodeError):
                    parsed_inputs = input_data

                with st.expander("View assessment inputs"):
                    st.json(parsed_inputs)
