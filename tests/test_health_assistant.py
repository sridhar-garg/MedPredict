from types import SimpleNamespace

import pytest
from google import genai

import health_assistant as assistant


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__("synthetic-secret-should-not-appear")


def fake_client(monkeypatch, responses, available=()):
    calls, clients = [], []

    class Client:
        def __init__(self, **kwargs):
            self.options = kwargs
            self.closed = False
            self.models = self
            self.lists = 0
            clients.append(self)

        def generate_content(self, **kwargs):
            calls.append(kwargs)
            value = responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return SimpleNamespace(text=value)

        def list(self):
            self.lists += 1
            return [SimpleNamespace(name="models/" + model, supported_actions=["generateContent"]) for model in available]

        def close(self):
            self.closed = True

    monkeypatch.setattr(genai, "Client", Client)
    return calls, clients


def test_guide_greeting_and_condition_response_without_credentials():
    greeting = assistant.answer_question([dict(role="user", content="hi")])
    assert greeting.mode == "library" and "Hello" in greeting.text
    answer = assistant.answer_question([dict(role="user", content="Explain epilepsy in simple terms")])
    assert answer.mode == "library" and not answer.provider_unavailable
    assert "### Epilepsy" in answer.text and "https://medlineplus.gov/epilepsy.html" in answer.text


@pytest.mark.parametrize("code", [401, 403, 429, 500])
def test_provider_failure_returns_labelled_guide_without_leaking_errors(monkeypatch, caplog, code):
    calls, clients = fake_client(monkeypatch, [ProviderError(code)])
    answer = assistant.answer_question([dict(role="user", content="epilepsy")], api_key="synthetic-test-key")
    assert answer.mode == "library" and answer.provider_unavailable
    assert answer.availability_message
    assert "Epilepsy" in answer.text
    assert len(calls) == 1 and clients[0].lists == 0 and clients[0].closed
    assert "synthetic-secret" not in answer.text + caplog.text + answer.availability_message
    assert "synthetic-test-key" not in caplog.text


def test_unavailable_model_uses_only_provider_advertised_replacement(monkeypatch):
    calls, clients = fake_client(monkeypatch, [ProviderError(404), "A real online answer"], ["gemini-3.7-flash"])
    answer = assistant.answer_question([dict(role="user", content="hi")], api_key="synthetic-test-key")
    assert answer.mode == "online" and answer.model == "gemini-3.7-flash"
    assert [call["model"] for call in calls] == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert calls[0]["config"].thinking_config.thinking_level.value == "LOW"
    assert calls[0]["config"].max_output_tokens == 4096
    assert clients[0].closed


def test_empty_provider_response_falls_back_and_closes_client(monkeypatch):
    calls, clients = fake_client(monkeypatch, [None])
    answer = assistant.answer_question([dict(role="user", content="asthma")], api_key="synthetic-test-key")
    assert answer.mode == "library" and answer.provider_unavailable
    assert "Asthma" in answer.text and clients[0].closed
