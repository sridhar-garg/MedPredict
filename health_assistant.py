"""Gemini 3.8 Flash text-chat support for MedPredict.

Security boundaries:
- No keys are embedded in code or printed.
- Chat history is kept by Streamlit in the browser session, not in SQLite.
- No access to medical scans, accounts or patient records unless the user types
  text into the chat box; Streamlit does not automatically forward data.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_USER_CHARS = 3000
MAX_HISTORY_MESSAGES = 12

SYSTEM_INSTRUCTION = """You are MedPredict AI, a helpful educational medical-research assistant.
You help users understand terminology, evaluate research, learn how machine-learning
classifiers work, and interpret what lab or scan terminology *means* in general.
You are NOT a clinician; do not claim to diagnose, confirm, exclude, or treat any
individual disease, or claim you have examined images or reports you have not seen.
Model confidence is not medical diagnostic probability. Clearly distinguish
established evidence, uncertainty, limitations, and suggestions for discussion
with a licensed healthcare professional. Avoid providing personalised treatment,
prescribing medications, dosage regimens or orders for medical tests. If the user
mentions severe symptoms or an emergency, recommend urgent local medical care.
For critical clinical claims, do not invent publications, numerical statistics,
URLs, or citations. If you cannot verify a source, state that clearly. Never
request passwords, API keys, identity documents, or identifiable patient data.
Keep answers clear, useful, and appropriately concise. Respond in the user's language.
"""


def load_settings(project_root: Path | None = None, secrets: Any = None) -> tuple[str, str]:
    """Resolve key from environment, .env and Streamlit Secrets.

    Explicit environment variables take precedence; Streamlit root secrets are
    also exposed via environment variables on Streamlit Community Cloud.
    """
    root = (project_root or Path(__file__).resolve().parent).resolve()
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=root / ".env", override=False)
    except ImportError:
        pass

    def pick(key: str) -> str:
        value = os.getenv(key, "").strip()
        if value:
            return value
        if secrets is not None:
            try:
                return str(secrets.get(key, "") or "").strip()
            except (KeyError, FileNotFoundError, RuntimeError, AttributeError, OSError):
                pass
        return ""

    api_key = pick("GEMINI_API_KEY") or pick("GOOGLE_API_KEY")
    model = pick("GEMINI_MODEL") or DEFAULT_MODEL
    return api_key, model


def bounded_history(history: list[dict[str, str]], *, max_messages: int = MAX_HISTORY_MESSAGES) -> list[dict[str, str]]:
    """Retain a bounded, alternating text conversation for stateless calls."""
    cleaned = []
    for item in history[-max_messages:]:
        role = item.get("role")
        message = item.get("content", "")
        if role not in ("user", "assistant") or not isinstance(message, str):
            continue
        cleaned.append({"role": role, "content": message[:MAX_USER_CHARS]})
    return cleaned


def to_genai_contents(history: list[dict[str, str]]) -> list[Any]:
    """Convert Streamlit role names to the SDK's 'user' and 'model' roles."""
    from google.genai import types
    return [
        types.Content(role="model" if item["role"] == "assistant" else "user",
                      parts=[types.Part.from_text(text=item["content"])])
        for item in bounded_history(history)
    ]


def generate_reply(history: list[dict[str, str]], *, api_key: str, model: str) -> str:
    """Send last conversation turns to Gemini without server-side chat storage.

    The caller must append the newest user turn to `history` before calling.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Missing GEMINI_API_KEY")
    if not history or history[-1].get("role") != "user":
        raise ValueError("The most recent turn must be a user message")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=to_genai_contents(history),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=2500,
            ),
        )
        result = (getattr(response, "text", None) or "").strip()
        if not result:
            raise RuntimeError("The model did not return a text response. Please retry.")
        return result
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def friendly_error(error: Exception) -> str:
    """Avoid exposing raw SDK errors containing request or account metadata."""
    msg = str(error).lower()
    if isinstance(error, ValueError) and "missing gemini_api_key" in msg:
        return "Add GEMINI_API_KEY to your local .env or Streamlit Cloud Secrets."
    if "401" in msg or "api key not valid" in msg or "invalid api key" in msg:
        return "Gemini rejected the API key. Check the key in .env or Streamlit Secrets."
    if "403" in msg or "permission denied" in msg:
        return "Gemini access was denied. Check that your API key can access this model."
    if "429" in msg or "quota" in msg or "rate limit" in msg:
        return "Gemini's quota or rate limit was reached. Check your API usage and retry later."
    if "404" in msg or "not found" in msg or "not supported" in msg:
        return "The selected Gemini model is unavailable to this key. Check GEMINI_MODEL."
    if "timeout" in msg or "connection" in msg:
        return "Couldn't reach Gemini. Check your internet connection and try again."
    return "Gemini couldn't complete the request. Check the app's server logs for the exception type."
