import sqlite3
import json


DATABASE_NAME = "healthai.db"






def get_connection():
    from storage import connect
    return connect(DATABASE_NAME)






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
        ORDER BY created_at DESC, id DESC
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
    from storage import database_url
    if database_url():
        # Hosted schema is deployed separately; never run SQLite DDL against Postgres.
        conn = get_connection()
        try:
            conn.cursor().execute("SELECT id FROM users LIMIT 0")
        finally:
            conn.close()
        return
    create_users_table()
    create_health_assessments_table()
    create_family_connections_table()
    create_workspace_tables()






if __name__ == "__disabled__":

    initialize_database()

    print(
        "Database, users table, health assessments table and "
        "family connections table created successfully!"
    )



def create_workspace_tables():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS google_identities (
            subject TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            display_name TEXT NOT NULL, rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            title TEXT NOT NULL, comment TEXT NOT NULL, context TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS workspace_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind TEXT NOT NULL, title TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            language TEXT NOT NULL DEFAULT 'en', theme TEXT NOT NULL DEFAULT 'light')""")
        cur.execute("CREATE INDEX IF NOT EXISTS workspace_user_date ON workspace_items(user_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS assessments_user_date ON health_assessments(user_id, created_at)")
        conn.commit()
    finally:
        conn.close()


def save_review(user_id, display_name, rating, title, comment, context):
    if not user_id or not get_user_profile(user_id):
        raise ValueError("Sign in to submit a review.")
    display_name, title, comment, context = [str(x).strip() for x in (display_name, title, comment, context)]
    if not 1 <= int(rating) <= 5 or not 2 <= len(display_name) <= 60 or not 3 <= len(title) <= 100 or not 10 <= len(comment) <= 1500 or not 1 <= len(context) <= 80:
        raise ValueError("Please complete all review fields within the displayed limits.")
    conn = get_connection()
    try:
        conn.cursor().execute("""INSERT INTO reviews(user_id,display_name,rating,title,comment,context)
            VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            display_name=excluded.display_name,rating=excluded.rating,title=excluded.title,
            comment=excluded.comment,context=excluded.context,updated_at=CURRENT_TIMESTAMP""",
            (user_id, display_name, int(rating), title, comment, context))
        conn.commit()
    finally:
        conn.close()


def get_reviews(user_id=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id,user_id,display_name,rating,title,comment,context,created_at,updated_at FROM reviews" +
                    (" WHERE user_id=?" if user_id is not None else "") + " ORDER BY updated_at DESC, id DESC",
                    (user_id,) if user_id is not None else ())
        keys = ('id','user_id','name','rating','title','comment','context','created_at','updated_at')
        return [dict(zip(keys, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def delete_review(user_id):
    conn = get_connection()
    try:
        conn.cursor().execute("DELETE FROM reviews WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def save_workspace_item(user_id, kind, title, payload):
    if not user_id:
        raise ValueError("Sign in to save your work.")
    data = json.dumps(payload, ensure_ascii=False, default=str)
    if len(data.encode('utf-8')) > 1_000_000:
        raise ValueError("This saved item is too large.")
    conn = get_connection()
    try:
        conn.cursor().execute("INSERT INTO workspace_items(user_id,kind,title,payload) VALUES(?,?,?,?)",
                              (user_id, kind, title, data))
        conn.commit()
    finally:
        conn.close()


def get_workspace_items(user_id, kind=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id,kind,title,payload,created_at FROM workspace_items WHERE user_id=?" +
                    (" AND kind=?" if kind else "") + " ORDER BY created_at DESC,id DESC", (user_id,kind) if kind else (user_id,))
        return [dict(id=r[0], kind=r[1], title=r[2], payload=json.loads(r[3]), created_at=str(r[4])) for r in cur.fetchall()]
    finally:
        conn.close()


def get_dashboard_records(user_id):
    """Return the account's dashboard metadata without inputs or saved payloads."""
    if user_id is None:
        return [], []
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, disease, prediction, probability, created_at
               FROM health_assessments WHERE user_id = ?
               ORDER BY created_at DESC, id DESC""",
            (user_id,),
        )
        assessments = [dict(id=i, disease=disease, prediction=prediction, probability=probability, created_at=created_at)
                       for i, disease, prediction, probability, created_at in cur.fetchall()]
        cur.execute(
            """SELECT kind, title, created_at FROM workspace_items
               WHERE user_id = ? AND kind IN ('Screenings', 'Reports', 'Imaging')
               ORDER BY created_at DESC, id DESC""",
            (user_id,),
        )
        work = [dict(kind=kind, title=title, created_at=created_at)
                for kind, title, created_at in cur.fetchall()]
        return assessments, work
    finally:
        conn.close()


def delete_workspace_item(user_id, item_id):
    conn = get_connection()
    try:
        conn.cursor().execute("DELETE FROM workspace_items WHERE id=? AND user_id=?", (item_id,user_id))
        conn.commit()
    finally:
        conn.close()


def load_preferences(user_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT language,theme FROM user_preferences WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return dict(language=row[0],theme=row[1]) if row else {}
    finally:
        conn.close()


def save_preferences(user_id, language, theme):
    conn = get_connection()
    try:
        conn.cursor().execute("""INSERT INTO user_preferences(user_id,language,theme) VALUES(?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET language=excluded.language,theme=excluded.theme""", (user_id,language,theme))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database()
