"""Start MedPredict on a direct HTTPS host, with secrets supplied at runtime.

Production requires Google OAuth and an explicitly configured durable database.
An independent, mounted SQLite store is permitted only when explicitly selected;
an unconfigured server must not silently create a second account database.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
GOOGLE_METADATA = "https://accounts.google.com/.well-known/openid-configuration"
LOCAL_DATA_DIR = Path("/data")
LOCAL_DB = LOCAL_DATA_DIR / "healthai.db"


def storage_mode(env):
    mode = env.get("MEDPREDICT_STORAGE", "postgres").strip().lower()
    uri = env.get("DATABASE_URL", "").strip()
    if mode == "postgres":
        if not uri.startswith(("postgresql://", "postgres://")):
            raise ValueError("Set DATABASE_URL to the private PostgreSQL connection URI.")
    elif mode == "sqlite":
        if uri:
            raise ValueError("SQLite mode cannot be combined with DATABASE_URL.")
        if env.get("MEDPREDICT_DB_PATH") != str(LOCAL_DB):
            raise ValueError(f"SQLite requires MEDPREDICT_DB_PATH={LOCAL_DB} on the durable data volume.")
    else:
        raise ValueError("MEDPREDICT_STORAGE must be postgres or sqlite.")
    return mode


def config_from_env(env):
    base = env.get("APP_BASE_URL", "").strip() or (
        "https://" + env["RAILWAY_PUBLIC_DOMAIN"].strip() if env.get("RAILWAY_PUBLIC_DOMAIN") else ""
    )
    if not base:
        raise ValueError("Set APP_BASE_URL or generate a Railway public domain.")
    url = urlsplit(base)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.path not in ("", "/") or url.query or url.fragment
            or any(c.isspace() for c in base)):
        raise ValueError("APP_BASE_URL must be a public HTTPS origin, without a path or query.")
    base = base.rstrip("/")
    storage_mode(env)
    required = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "MEDPREDICT_COOKIE_SECRET")
    missing = [key for key in required if not env.get(key, "").strip()]
    if missing:
        raise ValueError("Set these private deployment variables: " + ", ".join(missing))
    if not env["GOOGLE_CLIENT_ID"].endswith(".apps.googleusercontent.com"):
        raise ValueError("GOOGLE_CLIENT_ID must be a Google OAuth client ID.")
    if len(env["MEDPREDICT_COOKIE_SECRET"]) < 32:
        raise ValueError("MEDPREDICT_COOKIE_SECRET must have at least 32 characters.")
    secrets = {
        "auth": {
            "redirect_uri": base + "/oauth2callback",
            "cookie_secret": env["MEDPREDICT_COOKIE_SECRET"],
            "expose_tokens": [],
            "google": {
                "client_id": env["GOOGLE_CLIENT_ID"],
                "client_secret": env["GOOGLE_CLIENT_SECRET"],
                "server_metadata_url": GOOGLE_METADATA,
            },
        }
    }
    return base, secrets


def write_secrets(destination, secrets):
    destination.parent.mkdir(parents=True, exist_ok=True)
    auth = secrets["auth"]
    google = auth["google"]
    # TOML basic strings accept the same escaping as JSON strings. Keeping the
    # fixed schema explicit avoids an extra runtime dependency and interpolation.
    quoted = lambda value: json.dumps(value, ensure_ascii=False)
    content = "\n".join([
        "[auth]", "redirect_uri = " + quoted(auth["redirect_uri"]),
        "cookie_secret = " + quoted(auth["cookie_secret"]), "expose_tokens = []", "",
        "[auth.google]", "client_id = " + quoted(google["client_id"]),
        "client_secret = " + quoted(google["client_secret"]),
        "server_metadata_url = " + quoted(google["server_metadata_url"]), "",
    ])
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        os.chmod(temp_path, 0o600)
        handle.write(content)
    os.replace(temp_path, destination)


def main():
    try:
        base, secrets = config_from_env(os.environ)
        mode = storage_mode(os.environ)
        if mode == "sqlite" and (not LOCAL_DATA_DIR.is_mount() or not os.access(LOCAL_DATA_DIR, os.W_OK)):
            raise ValueError("SQLite requires a writable, persistent /data mount. Refusing ephemeral storage.")
        port = int(os.environ.get("PORT", "7860"))
        if not 1024 <= port <= 65535 or port == 8501:
            raise ValueError("PORT must be a nonprivileged port other than 8501.")
    except ValueError as error:
        sys.exit(str(error))
    os.chdir(ROOT)
    os.environ["APP_BASE_URL"] = base
    os.environ["PORT"] = str(port)
    write_secrets(ROOT / ".streamlit" / "secrets.toml", secrets)
    # Check the existing shared schema, or initialize explicitly selected SQLite storage.
    # Do not migrate, copy or replace existing data.
    from database import initialize_database
    try:
        initialize_database()
    except Exception:
        sys.exit("The configured durable database could not be opened or its MedPredict schema is unavailable.")

    children = []
    def stop(*_):
        for process in children:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless", "true", "--server.address", "127.0.0.1", "--server.port", "8501",
            "--server.enableCORS", "true", "--server.enableXsrfProtection", "true",
            "--browser.serverAddress", urlsplit(base).hostname, "--browser.serverPort", "443",
            "--browser.gatherUsageStats", "false", "--client.toolbarMode", "minimal",
        ]))
        children.append(subprocess.Popen(["caddy", "run", "--config", str(ROOT / "deploy" / "Caddyfile"), "--adapter", "caddyfile"]))
        while all(process.poll() is None for process in children):
            time.sleep(0.5)
        return next((process.returncode for process in children if process.returncode), 0)
    finally:
        stop()
        for process in children:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
