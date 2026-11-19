"""One validated deployment URL shared by both installable app builders."""
import re
from urllib.parse import urlsplit


def release_url(value):
    value = value.strip()
    url = urlsplit(value)
    host = url.hostname or ""
    if (url.scheme != "https" or not re.fullmatch(r"[a-z0-9.-]+\.[a-z0-9.-]+", host)
            or url.netloc.lower() != host or url.path not in ("", "/")
            or url.query or url.fragment or len(value) > 200):
        raise ValueError("Supply the deployment's HTTPS root URL, without a path, port, query, or credentials.")
    if host == "streamlit.app" or host.endswith(".streamlit.app"):
        raise ValueError("Use the independent deployment, not Streamlit Community Cloud.")
    return "https://" + host + "/"
