"""Appels aux moteurs : question envoyée telle quelle, erreurs lisibles et sans clé. Aucun appel réel."""

import asyncio
import json
from types import SimpleNamespace

import httpx

import services.llm as llm
from config import settings
from services.llm import describe_error, redact_secrets
from tests.test_api import _token, client  # noqa: F401  (fixture)

PROMPT = "What are the best customer experience agencies in Europe?"


def _capture(monkeypatch, status=200, body=None):
    """Remplace le client HTTP des moteurs par un faux qui garde les requêtes."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body if body is not None else {"output_text": "ok", "output": []})

    real = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: real(transport=httpx.MockTransport(handler), **kwargs))
    keys = {**settings.__dict__, "openai_api_key": "sk-test-openai-123456", "perplexity_api_key": "pplx-test-123456",
            "gemini_api_key": "AIzaTestGeminiKey123456", "mock_llm": "false"}
    monkeypatch.setattr(llm, "settings", SimpleNamespace(**keys, provider_mode=lambda provider: "live"))
    return seen


def test_questions_are_sent_without_any_instruction(monkeypatch):
    seen = _capture(monkeypatch)
    asyncio.run(llm.complete("openai", PROMPT, [], "n"))
    asyncio.run(llm.complete("perplexity", PROMPT, [], "n"))
    openai, perplexity = (json.loads(request.content) for request in seen)
    assert openai["input"] == PROMPT and "instructions" not in openai
    assert perplexity["input"] == PROMPT


def test_gemini_key_travels_in_a_header(monkeypatch):
    seen = _capture(monkeypatch, body={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
    asyncio.run(llm.complete("gemini", PROMPT, [], "n"))
    assert "key=" not in str(seen[0].url)
    assert seen[0].headers["x-goog-api-key"] == "AIzaTestGeminiKey123456"


def test_engine_errors_are_readable_and_hide_keys(monkeypatch):
    _capture(monkeypatch, status=404, body={"error": {"message": "models/gemini-x is not found"}})
    result = asyncio.run(llm.complete("gemini", PROMPT, [], "n"))
    assert result.error == "Erreur 404 (modèle ou adresse introuvable) : models/gemini-x is not found"
    timeout = httpx.ReadTimeout("lent", request=httpx.Request("POST", "https://api.perplexity.ai/v1/agent"))
    assert describe_error(timeout) == "Le moteur n'a pas répondu à temps (60 s)."
    old = "Client error '404 Not Found' for url 'https://x.googleapis.com/v1/m:generate?key=AIzaSyRealKey12345&alt=1'"
    assert "AIzaSyRealKey12345" not in redact_secrets(old)
    assert "sk-proj-abcdefghijkl" not in redact_secrets("Bearer sk-proj-abcdefghijkl refusée")


def test_saving_a_new_domain_does_not_launch_a_site_audit(client):  # noqa: F811
    headers = {"Authorization": f"Bearer {_token(client)}"}
    before = client.get("/api/v1/audit", headers=headers).json()["audit"]["id"]
    current = client.get("/api/v1/settings", headers=headers).json()
    saved = client.put("/api/v1/settings", headers=headers, json={**current, "domain": "nouveau-site.io"})
    assert saved.status_code == 200
    assert client.get("/api/v1/audit", headers=headers).json()["audit"]["id"] == before
