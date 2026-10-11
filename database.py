import sqlite3
import json


DATABASE_NAME = "healthai.db"






def get_connection():
    return sqlite3.connect(DATABASE_NAME)






def create_users_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            username TEXT UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )







    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]

    if "username" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN username TEXT"
        )

    if "password_hash" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN password_hash TEXT"
        )

    conn.commit()
    conn.close()






def create_health_assessments_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS health_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            disease TEXT NOT NULL,
            input_data TEXT,
            prediction TEXT,
            probability REAL,
            evaluation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()






def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, email, name, created_at
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    user = cursor.fetchone()

    conn.close()

    return user


def get_user_by_username(username):
    """
    Retrieve a user using their username.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, email, name, username, password_hash, created_at
        FROM users
        WHERE username = ?
        """,
        (username,)
    )

    user = cursor.fetchone()

    conn.close()

    return user






def create_user(email, name=None, username=None, password_hash=None):
    if not email:
        raise ValueError("Email address is required.")

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

        return cursor.lastrowid

    finally:
        conn.close()






def update_user_credentials(user_id, username, password_hash):
    """
    Add or update username and password for an existing user.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE users
            SET username = ?,
                password_hash = ?
            WHERE id = ?
            """,
            (
                username,
                password_hash,
                user_id
            )
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:
        conn.close()






def update_user_name(user_id, name):
    """
    Update the name of an existing user.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE users
            SET name = ?
            WHERE id = ?
            """,
            (
                name,
                user_id
            )
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:
        conn.close()






def get_user_profile(user_id):
    """
    Retrieve complete profile information for a user.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            email,
            name,
            username,
            created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    conn.close()

    return user






def save_health_assessment(
    user_id,
    disease,
    input_data,
    prediction,
    probability,
    evaluation
):
    """
    Save a completed health assessment for a logged-in user.
    """

    if user_id is None:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO health_assessments (
                user_id,
                disease,
                input_data,
                prediction,
                probability,
                evaluation
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                disease,
                json.dumps(input_data),
                prediction,
                probability,
                evaluation,
            )
        )

        conn.commit()

        return True

    except Exception as e:
        print("Error saving health assessment:", e)
        return False

    finally:
        conn.close()






def get_health_assessments(user_id):
    """
    Retrieve all saved assessments belonging to a user.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            disease,
            input_data,
            prediction,
            probability,
            evaluation,
            created_at
        FROM health_assessments
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    assessments = cursor.fetchall()

    conn.close()

    return assessments






def create_family_connections_table():
    """
    Create the table used for permission-based family connections.

    A connection starts as 'pending' and becomes 'accepted' only
    after the recipient accepts it.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS family_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            member_user_id INTEGER NOT NULL,
            relationship TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_user_id, member_user_id),
            FOREIGN KEY (owner_user_id) REFERENCES users(id),
            FOREIGN KEY (member_user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


def find_family_user(identifier, current_user_id=None):
    """
    Find a registered user by username or email.

    The logged-in user cannot add themselves.
    Returns:
        id, email, name, username
    """

    identifier = (identifier or "").strip()

    if not identifier:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, email, name, username
        FROM users
        WHERE username = ? OR email = ?
        LIMIT 1
        """,
        (identifier, identifier)
    )

    user = cursor.fetchone()
    conn.close()

    if user and current_user_id is not None and user[0] == current_user_id:
        return None

    return user


def add_family_connection(owner_user_id, member_user_id, relationship):
    """
    Send a family connection request.

    The owner_user_id is the person sending the request.
    The member_user_id is the recipient.
    """

    if owner_user_id is None or member_user_id is None:
        return False, "Invalid user."

    if owner_user_id == member_user_id:
        return False, "You cannot add yourself."

    relationship = (relationship or "").strip()

    if not relationship:
        return False, "Please select a relationship."

    conn = get_connection()
    cursor = conn.cursor()

    try:


        cursor.execute(
            """
            SELECT id, owner_user_id, member_user_id, status
            FROM family_connections
            WHERE
                (owner_user_id = ? AND member_user_id = ?)
                OR
                (owner_user_id = ? AND member_user_id = ?)
            LIMIT 1
            """,
            (
                owner_user_id,
                member_user_id,
                member_user_id,
                owner_user_id
            )
        )

        existing = cursor.fetchone()

        if existing:
            connection_id, old_owner, old_member, status = existing

            if status == "accepted":
                return False, "You are already connected."

            if status == "pending":
                return False, "A family request is already pending."

            cursor.execute(
                """
                UPDATE family_connections
                SET owner_user_id = ?,
                    member_user_id = ?,
                    relationship = ?,
                    status = 'pending',
                    created_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    owner_user_id,
                    member_user_id,
                    relationship,
                    connection_id
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO family_connections (
                    owner_user_id,
                    member_user_id,
                    relationship,
                    status
                )
                VALUES (?, ?, ?, 'pending')
                """,
                (
                    owner_user_id,
                    member_user_id,
                    relationship
                )
            )

        conn.commit()
        return True, "Family request sent."

    except sqlite3.IntegrityError:
        return False, "A family request already exists."

    finally:
        conn.close()


def get_pending_family_requests(user_id):
    """
    Get incoming pending family requests for the logged-in user.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            fc.id,
            fc.owner_user_id,
            u.name,
            u.username,
            u.email,
            fc.relationship,
            fc.created_at
        FROM family_connections fc
        JOIN users u
            ON u.id = fc.owner_user_id
        WHERE fc.member_user_id = ?
          AND fc.status = 'pending'
        ORDER BY fc.created_at DESC
        """,
        (user_id,)
    )

    requests = cursor.fetchall()
    conn.close()

    return requests


def get_family_connections(user_id):
    """
    Get all accepted family connections for the logged-in user.

    The function returns connections in either direction, so both
    family members can see the relationship after acceptance.

    Tuple:
        connection_id,
        other_user_id,
        other_name,
        other_username,
        other_email,
        relationship,
        created_at
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            fc.id,
            CASE
                WHEN fc.owner_user_id = ? THEN fc.member_user_id
                ELSE fc.owner_user_id
            END AS other_user_id,
            CASE
                WHEN fc.owner_user_id = ? THEN member.name
                ELSE owner.name
            END AS other_name,
            CASE
                WHEN fc.owner_user_id = ? THEN member.username
                ELSE owner.username
            END AS other_username,
            CASE
                WHEN fc.owner_user_id = ? THEN member.email
                ELSE owner.email
            END AS other_email,
            fc.relationship,
            fc.created_at
        FROM family_connections fc
        JOIN users owner
            ON owner.id = fc.owner_user_id
        JOIN users member
            ON member.id = fc.member_user_id
        WHERE
            (fc.owner_user_id = ? OR fc.member_user_id = ?)
            AND fc.status = 'accepted'
        ORDER BY fc.created_at DESC
        """,
        (
            user_id,
            user_id,
            user_id,
            user_id,
            user_id,
            user_id
        )
    )

    connections = cursor.fetchall()
    conn.close()

    return connections


def accept_family_connection(connection_id, user_id):
    """
    Accept an incoming request.

    Only the recipient (member_user_id) can accept it.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE family_connections
            SET status = 'accepted'
            WHERE id = ?
              AND member_user_id = ?
              AND status = 'pending'
            """,
            (connection_id, user_id)
        )

        conn.commit()
        return cursor.rowcount > 0

    finally:
        conn.close()


def decline_family_connection(connection_id, user_id):
    """
    Decline an incoming request.

    Only the recipient can decline it.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM family_connections
            WHERE id = ?
              AND member_user_id = ?
              AND status = 'pending'
            """,
            (connection_id, user_id)
        )

        conn.commit()
        return cursor.rowcount > 0

    finally:
        conn.close()


def revoke_family_connection(connection_id, user_id):
    """
    Remove an accepted family connection.

    Either participant can revoke the connection.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM family_connections
            WHERE id = ?
              AND (owner_user_id = ? OR member_user_id = ?)
              AND status = 'accepted'
            """,
            (
                connection_id,
                user_id,
                user_id
            )
        )

        conn.commit()
        return cursor.rowcount > 0

    finally:
        conn.close()


def can_access_family_reports(owner_user_id, member_user_id):
    """
    Health-report access is allowed only when the two users have
    an accepted family connection.
    """

    if owner_user_id is None or member_user_id is None:
        return False

    if owner_user_id == member_user_id:
        return True

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM family_connections
        WHERE
            (
                (owner_user_id = ? AND member_user_id = ?)
                OR
                (owner_user_id = ? AND member_user_id = ?)
            )
            AND status = 'accepted'
        LIMIT 1
        """,
        (
            owner_user_id,
            member_user_id,
            member_user_id,
            owner_user_id
        )
    )

    allowed = cursor.fetchone() is not None
    conn.close()

    return allowed


def get_family_assessments(owner_user_id, member_user_id):
    """
    Return another user's health assessments only when an accepted
    family connection grants access.
    """

    if not can_access_family_reports(owner_user_id, member_user_id):
        return []

    return get_health_assessments(member_user_id)



def process_family_email_action(connection_id, recipient_user_id, action):
    action = (action or "").lower().strip()
    if action not in ("accept", "decline"):
        return False, "Invalid family email action.", None
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT fc.id, u.email, fc.status FROM family_connections fc "
            "JOIN users u ON u.id=fc.owner_user_id "
            "WHERE fc.id=? AND fc.member_user_id=? LIMIT 1",
            (connection_id, recipient_user_id),
        )
        row = cur.fetchone()
        if not row:
            return False, "This family request could not be found.", None
        if row[2] != "pending":
            return False, "This family request is no longer pending.", row[1]
        if action == "accept":
            cur.execute(
                "UPDATE family_connections SET status='accepted' "
                "WHERE id=? AND member_user_id=? AND status='pending'",
                (connection_id, recipient_user_id),
            )
            msg = "Family connection accepted."
        else:
            cur.execute(
                "DELETE FROM family_connections "
                "WHERE id=? AND member_user_id=? AND status='pending'",
                (connection_id, recipient_user_id),
            )
            msg = "Family request declined."
        conn.commit()
        ok = cur.rowcount > 0
        return ok, (msg if ok else "This family request is no longer available."), row[1]
    finally:
        conn.close()





def initialize_database():
    create_users_table()
    create_health_assessments_table()
    create_family_connections_table()






if __name__ == "__main__":

    initialize_database()

    print(
        "Database, users table, health assessments table and "
        "family connections table created successfully!"
    )
