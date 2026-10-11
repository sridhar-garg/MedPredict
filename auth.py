import os
import secrets
import smtplib
import hashlib
import hmac

from dotenv import load_dotenv
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    get_connection,
    get_user_by_username,
    update_user_credentials,
    create_user as db_create_user,
)






load_dotenv()






def generate_otp():
    """
    Generate a secure 6-digit OTP.
    """

    return str(
        secrets.randbelow(900000) + 100000
    )






def send_email_otp(receiver_email, otp):
    """
    Send a 6-digit OTP to the user's email address
    using Gmail SMTP.
    """

    sender_email = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")





    if not sender_email or not app_password:
        print(
            "Gmail credentials are missing from .env"
        )
        return False





    message = EmailMessage()

    message["Subject"] = (
        "HealthGuard AI - Login OTP"
    )

    message["From"] = sender_email
    message["To"] = receiver_email

    message.set_content(
        f"""Hello,

Your HealthGuard AI verification OTP is:

{otp}

This OTP is valid for your account verification.

If you did not request this OTP, please ignore this email.

Regards,
HealthGuard AI
"""
    )





    try:

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:

            smtp.login(
                sender_email,
                app_password
            )

            smtp.send_message(message)

        print(
            "Email OTP sent successfully."
        )

        return True

    except Exception as e:

        print(
            "Error sending email:",
            e
        )

        return False






def send_family_request_email(
    receiver_email,
    sender_name,
    sender_username,
    relationship,
):
    """
    Send the family notification using the same Gmail SMTP flow
    that successfully delivered the OTP test email.
    """

    sender_email = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("Gmail credentials are missing from .env")
        return False

    display_sender = sender_name or sender_username or "A HealthGuard AI user"

    message = EmailMessage()
    message["Subject"] = "HealthGuard AI - New Family Connection Request"
    message["From"] = sender_email
    message["To"] = receiver_email

    message.set_content(
        f"""Hello,

You have received a new family connection request on HealthGuard AI.

From: {display_sender}
Username: @{sender_username or "user"}
Relationship: {relationship}

Please log in to HealthGuard AI and open Family Health to accept or decline this request.

Your health information will remain private until the request is accepted.

If you did not expect this request, you can simply decline it from the Family Health page.

Regards,
HealthGuard AI
"""
    )

    print("\n========== FAMILY EMAIL ==========")
    print("Sender:", sender_email)
    print("Recipient:", receiver_email)
    print("Subject:", message["Subject"])

    try:

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(message)

        print("Gmail SMTP accepted the family email.")
        print("==================================\n")
        return True

    except Exception as e:
        print("FAMILY EMAIL FAILED:", repr(e))
        print("==================================\n")
        return False


def send_family_acceptance_email(
    receiver_email,
    accepter_name,
    accepter_username,
    relationship,
):
    """Notify the original requester that the family request was accepted."""

    sender_email = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("Gmail credentials are missing from .env")
        return False

    display_accepter = accepter_name or accepter_username or "Your family member"

    message = EmailMessage()
    message["Subject"] = "HealthGuard AI - Family Connection Accepted"
    message["From"] = sender_email
    message["To"] = receiver_email

    message.set_content(
        f"""Hello,

Your HealthGuard AI family connection request has been accepted.

Family member: {display_accepter}
Username: @{accepter_username or "user"}
Relationship: {relationship}

You can now open Family Health in HealthGuard AI to view your accepted family connection.

Regards,
HealthGuard AI
"""
    )

    print("\n========== FAMILY ACCEPTANCE EMAIL ==========")
    print("Sender:", sender_email)
    print("Recipient:", receiver_email)
    print("Subject:", message["Subject"])

    try:

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(message)

        print("Gmail SMTP accepted the family acceptance email.")
        print("==============================================\n")
        return True

    except Exception as e:
        print("FAMILY ACCEPTANCE EMAIL FAILED:", repr(e))
        print("==============================================\n")
        return False

def get_user_by_email(email):
    """
    Find an existing user using their email address.

    Returns:
        (id, email, name, created_at)
        or None if the user does not exist.
    """

    if not email:
        return None

    email = email.strip().lower()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            email,
            name,
            created_at
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    user = cursor.fetchone()

    conn.close()

    return user



def create_family_email_token(connection_id, recipient_user_id):
    import base64, time
    secret = os.getenv("GMAIL_APP_PASSWORD")
    if not secret:
        raise RuntimeError("GMAIL_APP_PASSWORD is required to create family email links.")
    payload = f"{connection_id}:{recipient_user_id}:{int(time.time())}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode().rstrip("=")


def verify_family_email_token(token, max_age_seconds=86400):
    import base64, time
    secret = os.getenv("GMAIL_APP_PASSWORD")
    if not secret or not token:
        return None
    try:
        raw = base64.urlsafe_b64decode((token + "=" * (-len(token) % 4)).encode()).decode()
        connection_id, recipient_user_id, issued_at, sig = raw.split(":", 3)
        payload = f"{connection_id}:{recipient_user_id}:{issued_at}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(time.time()) - int(issued_at) > max_age_seconds:
            return None
        return int(connection_id), int(recipient_user_id)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def send_family_request_email_with_buttons(receiver_email, sender_name, sender_username, relationship, connection_id, recipient_user_id):
    import html
    from urllib.parse import urlencode
    sender_email = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    base_url = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    if not sender_email or not app_password:
        return False, "Gmail credentials are missing from .env."
    if not base_url:
        return False, "APP_BASE_URL is missing from .env. Set it to the public Streamlit app URL."
    token = create_family_email_token(connection_id, recipient_user_id)
    accept_url = f"{base_url}/?{urlencode({'family_action':'accept','family_token':token})}"
    decline_url = f"{base_url}/?{urlencode({'family_action':'decline','family_token':token})}"
    display = sender_name or sender_username or "A HealthGuard AI user"
    message = EmailMessage()
    message["Subject"] = "HealthGuard AI - New Family Connection Request"
    message["From"] = sender_email
    message["To"] = receiver_email
    message.set_content(
        f"Hello,\n\nYou have received a new family connection request from {display}.\n"
        f"Relationship: {relationship}\n\nAccept: {accept_url}\nDecline: {decline_url}\n\n"
        "These links are valid for 24 hours.\n\nRegards,\nHealthGuard AI"
    )
    html_body = (
        '<html><body style="font-family:Arial,sans-serif;color:#10233f">'
        '<h2>HealthGuard AI</h2>'
        '<p>You have received a new family connection request.</p>'
        f'<p><b>From:</b> {html.escape(display)}<br>'
        f'<b>Username:</b> @{html.escape(sender_username or "user")}<br>'
        f'<b>Relationship:</b> {html.escape(relationship or "Family Member")}</p>'
        f'<p><a href="{html.escape(accept_url, quote=True)}" '
        'style="display:inline-block;padding:12px 22px;background:#0ca78d;color:white;text-decoration:none;border-radius:8px;font-weight:bold">'
        '✓ Accept</a>&nbsp;&nbsp;'
        f'<a href="{html.escape(decline_url, quote=True)}" '
        'style="display:inline-block;padding:12px 22px;background:#e8eef5;color:#10233f;text-decoration:none;border-radius:8px;font-weight:bold">'
        'Decline</a></p>'
        '<p style="font-size:12px;color:#7186a0">Links expire after 24 hours. Health information remains private until accepted.</p>'
        '</body></html>'
    )
    message.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(message)
        return True, f"Gmail accepted the email for {receiver_email}."
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"





def create_user(
    email,
    name=None,
    username=None,
    password_hash=None
):
    """
    Create a new user.

    Username and password_hash are optional so this function
    remains compatible with the existing OTP account flow.
    """

    if not email:
        raise ValueError(
            "Email address is required."
        )

    email = email.strip().lower()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users (
                email,
                name,
                username,
                password_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                email,
                name,
                username,
                password_hash
            )
        )

        conn.commit()

        user_id = cursor.lastrowid

        return user_id

    finally:

        conn.close()






def hash_password(password):
    """
    Hash a password securely before saving it to the database.

    New passwords use Werkzeug's secure password hashing format.
    The actual password is never stored in the database.
    """

    if not password:
        raise ValueError("Password is required.")

    return generate_password_hash(password)


def _verify_legacy_custom_pbkdf2(password, password_hash):
    """
    Verify passwords created by an older HealthGuard AI version that used:
    pbkdf2_sha256$200000$salt$digest
    """
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)

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


def verify_password(password, password_hash):
    """
    Verify a password against the stored hash.

    Supports:
    1. Current Werkzeug hashes.
    2. Older custom PBKDF2 hashes.
    3. Older SHA-256 hashes.

    This lets existing accounts continue to work while all newly
    created/changed passwords use the current secure format.
    """

    if not password or not password_hash:
        return False


    try:
        if check_password_hash(password_hash, password):
            return True
    except (ValueError, TypeError):
        pass


    if password_hash.startswith("pbkdf2_sha256$"):
        return _verify_legacy_custom_pbkdf2(password, password_hash)


    if len(password_hash) == 64:
        try:
            entered_hash = hashlib.sha256(
                password.encode("utf-8")
            ).hexdigest()

            return hmac.compare_digest(
                entered_hash,
                password_hash
            )
        except Exception:
            return False

    return False






def get_user_by_username_auth(username):
    """
    Find a user using their username.
    """

    if not username:
        return None

    username = username.strip().lower()

    return get_user_by_username(username)






def username_exists(username):
    """
    Check whether a username is already registered.
    """

    if not username:
        return False

    username = username.strip().lower()

    user = get_user_by_username(username)

    return user is not None






def authenticate_user(username, password):
    """
    Authenticate an existing user using
    username and password.

    Returns:
        User record if login is successful.
        None if username/password is incorrect.

    User record:
        id,
        email,
        name,
        username,
        password_hash,
        created_at
    """

    if not username or not password:
        return None

    username = username.strip().lower()

    user = get_user_by_username(username)

    if user is None:
        return None












    stored_password_hash = user[4]

    if not stored_password_hash:
        return None

    if verify_password(
        password,
        stored_password_hash
    ):


        if not stored_password_hash.startswith(("scrypt:", "pbkdf2:")):
            try:
                new_hash = hash_password(password)
                update_user_credentials(
                    user[0],
                    user[3],
                    new_hash
                )
            except Exception:


                pass

        return user

    return None






def create_account(
    email,
    username,
    password,
    name=None
):
    """
    Create a completely new HealthGuard AI account.

    Expected flow:

        Email
          ↓
        OTP
          ↓
        Username + Password
          ↓
        Account created
    """

    if not email:
        raise ValueError(
            "Email address is required."
        )

    if not username:
        raise ValueError(
            "Username is required."
        )

    if not password:
        raise ValueError(
            "Password is required."
        )

    email = email.strip().lower()
    username = username.strip().lower()





    existing_email_user = get_user_by_email(email)

    if existing_email_user is not None:
        raise ValueError(
            "An account with this email already exists."
        )





    if username_exists(username):
        raise ValueError(
            "This username is already taken."
        )





    password_hash = hash_password(password)





    return create_user(
        email=email,
        name=name,
        username=username,
        password_hash=password_hash
    )






def set_user_credentials(
    user_id,
    username,
    password
):
    """
    Add username and password to an existing account.

    This is useful for users who were created previously
    using the old email + OTP system.
    """

    if not user_id:
        raise ValueError(
            "User ID is required."
        )

    if not username:
        raise ValueError(
            "Username is required."
        )

    if not password:
        raise ValueError(
            "Password is required."
        )

    username = username.strip().lower()





    existing_user = get_user_by_username(username)

    if existing_user is not None:


        if existing_user[0] != user_id:
            raise ValueError(
                "This username is already taken."
            )





    password_hash = hash_password(password)





    return update_user_credentials(
        user_id,
        username,
        password_hash
    )