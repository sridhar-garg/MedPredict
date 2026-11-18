"""Online Gemini support and an explicitly labelled offline condition guide.

Security boundaries:
- No keys are embedded in code or printed.
- Completed exchanges are saved by the caller to the account workspace.
- No access to medical scans, accounts or patient records unless the user types
  text into the chat box; Streamlit does not automatically forward data.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_USER_CHARS = 3000
MAX_HISTORY_MESSAGES = 12
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssistantAnswer:
    text: str
    mode: str
    model: str = ""
    provider_unavailable: bool = False
    availability_message: str = ""

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


def generate_online_reply(history: list[dict[str, str]], *, api_key: str, model: str) -> AssistantAnswer:
    """Send last conversation turns to Gemini without server-side chat storage.

    The caller must append the newest user turn to `history` before calling.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Missing GEMINI_API_KEY")
    if not history or history[-1].get("role") != "user":
        raise ValueError("The most recent turn must be a user message")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=20000, retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        def request(selected):
            options = dict(system_instruction=SYSTEM_INSTRUCTION, max_output_tokens=4096)
            if selected.removeprefix("models/").startswith("gemini-3"):
                options["thinking_config"] = types.ThinkingConfig(thinking_level="low")
            return client.models.generate_content(model=selected, contents=to_genai_contents(history),
                                                  config=types.GenerateContentConfig(**options))
        selected = model.removeprefix("models/")
        try:
            response = request(selected)
        except Exception as exc:
            # Only switch models after the provider reports a model error. Never
            # turn permission/quota failures into repeated chargeable requests.
            code = getattr(exc, "code", getattr(exc, "status_code", None))
            if str(code) not in ("400", "404") or (str(code) == "400" and "model" not in str(exc).lower()):
                raise
            available = {entry.name.removeprefix("models/") for entry in client.models.list()
                         if "generateContent" in (getattr(entry, "supported_actions", None) or [])}
            preferred = (DEFAULT_MODEL, "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite")
            replacement = next((name for name in preferred if name != selected and name in available), None)
            if replacement is None:
                raise
            selected = replacement
            response = request(selected)
        result = (getattr(response, "text", None) or "").strip()
        if not result:
            raise RuntimeError("The model did not return a text response. Please retry.")
        return AssistantAnswer(result, "online", selected)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def generate_reply(history, *, api_key, model):
    """Compatibility wrapper for existing callers."""
    return generate_online_reply(history, api_key=api_key, model=model).text


def library_reply(prompt):
    """Deterministic source retrieval; it is never presented as a model response."""
    from condition_library import library, normalize, search_topics
    query = normalize(prompt)
    if query in ("hi", "hello", "hey", "namaste", "good morning", "good evening"):
        return "Hello! I can help you explore health conditions and explain terms. Try **What is epilepsy?**, **Explain asthma**, or **What is AUROC?** You can also browse the condition library."
    if "auroc" in query or "roc curve" in query:
        return "**AUROC** describes how well a classifier ranks positive cases above negative cases across decision thresholds. A value near 0.5 is similar to chance ranking; 1.0 means perfect ranking in that evaluated dataset. It does not tell you whether an individual person has a disease, and it does not establish that a model works reliably in a different population."
    if "shap" in query:
        return "**SHAP** explains how input features influence a model's prediction relative to a baseline. A contribution describes the model's behaviour; it does not prove that a feature caused a disease. In an assessment, compare the feature explanation with the model limitations and the information you entered."
    if "ct" in query.split() and "mri" in query.split():
        return "**CT** uses X-rays to create cross-sectional images. **MRI** uses magnetic fields and radio waves. They show different kinds of detail and are chosen for different clinical questions. A qualified professional decides which examination is appropriate.\n\nSources: [CT](https://medlineplus.gov/ctscans.html) · [MRI](https://medlineplus.gov/mriscans.html)."
    matches = search_topics(prompt, limit=3)
    if not matches:
        found = []
        for topic in library()["topics"]:
            names = [normalize(topic["title"])] + [normalize(x) for x in topic["aliases"]]
            if any(len(name) >= 5 and f" {name} " in f" {query} " for name in names):
                found.append(topic)
        matches = sorted(found, key=lambda x: (not x["featured"], -len(x["title"])))[:2]
    if matches:
        topic = matches[0]
        paragraphs = topic["summary"].split("\n\n")[:4]
        return f"### {topic['title']}\n\n" + "\n\n".join(paragraphs) + f"\n\n[Read the MedlinePlus source]({topic['url']}). This is general health information, not a diagnosis for you."
    return "I can look up condition information and explain common assessment terms. Try a condition name such as **epilepsy**, **asthma**, **migraine** or **dengue**, or ask about **SHAP** or **AUROC**. For an open-ended conversation, choose Online AI when it is available."


def answer_question(history, *, api_key="", model=DEFAULT_MODEL, use_online=True):
    if not history or history[-1].get("role") != "user":
        raise ValueError("The most recent turn must be a user message")
    if use_online and api_key:
        try:
            return generate_online_reply(history, api_key=api_key, model=model)
        except Exception as exc:
            code = getattr(exc, "code", getattr(exc, "status_code", "unavailable"))
            logger.warning("Online assistant failed: %s, status=%s", type(exc).__name__, code)
            status = str(code)
            message = ("Online chat has reached its usage limit. Please try again later." if status == "429"
                       else "The online AI model is unavailable right now." if status == "404"
                       else "Online AI could not respond right now. You can retry later.")
            return AssistantAnswer(library_reply(history[-1]["content"]), "library", provider_unavailable=True,
                                   availability_message=message)
    return AssistantAnswer(library_reply(history[-1]["content"]), "library")


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
