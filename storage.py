"""Server-only persistence: Supabase Postgres, with SQLite for local demos.

DATABASE_URL belongs in Streamlit Secrets/environment, never in client HTML.
A configured cloud failure is never silently redirected to a local database.
"""
import os
import re
import sqlite3
from pathlib import Path


def database_url():
    value = os.getenv("DATABASE_URL", "")
    if not value:
        try:
            import streamlit as st
            value = st.secrets.get("DATABASE_URL", "")
        except (FileNotFoundError, KeyError):
            pass
    return value


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql, parameters=()):
        # Existing queries are parameterized SQLite statements; no user SQL is accepted.
        sql = sql.replace("?", "%s")
        returns_id = bool(re.match(r"\s*INSERT\s+INTO\s+users\b", sql, re.I))
        if returns_id:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        try:
            self._cursor.execute(sql, parameters)
        except Exception as exc:
            import psycopg
            if isinstance(exc, psycopg.IntegrityError):
                raise sqlite3.IntegrityError("A record with these details already exists.") from exc
            raise
        if returns_id:
            self.lastrowid = self._cursor.fetchone()[0]
        return self

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnection:
    def __init__(self, url):
        import psycopg
        self._connection = psycopg.connect(url, sslmode="require", connect_timeout=10,
                                          options="-c search_path=medpredict,pg_catalog")

    def cursor(self):
        return PostgresCursor(self._connection.cursor())

    def __getattr__(self, name):
        return getattr(self._connection, name)


def connect(local_path):
    url = database_url()
    if url:
        return PostgresConnection(url)
    target = os.getenv("MEDPREDICT_DB_PATH", str(local_path))
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=15)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection
