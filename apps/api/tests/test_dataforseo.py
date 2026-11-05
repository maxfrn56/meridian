"""Moteurs via DataForSEO. Aucun appel réel : un faux serveur renvoie les formats de la documentation."""

import asyncio
import base64
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

import services.dataforseo as dataforseo
import services.llm as llm
from config import settings
from services.dataforseo import DataForSEOError, ask, build_task, guess_language
from services.tracker import BatchResult

PROMPT = "Welk bureau kan ons helpen met customer experience en klantreizen in Nederland?"


def _envelope(result=None, task_code=20000, task_message="Ok.", top_code=20000):
    return {
        "status_code": top_code,
        "status_message": "Ok." if top_code == 20000 else "Refus",
        "cost": 0.004,
        "tasks": [{"status_code": task_code, "status_message": task_message, "result": [result] if result else None}],
    }


@pytest.fixture()
def credentials(monkeypatch):
    fake = SimpleNamespace(
        **{**settings.__dict__, "dataforseo_login": "login@test", "dataforseo_password": "secret-pass"},
    )
    monkeypatch.setattr(dataforseo, "settings", fake)
    return fake


def _client(payload, seen):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_language_is_guessed_from_the_question(credentials):
    assert guess_language(PROMPT) == "nl"
    assert guess_language("What are the best customer experience agencies in Europe?") == "en"
    assert guess_language("Quelle agence CX choisir pour une PME à Bordeaux ?") == "fr"
    assert guess_language("NPS ?") == "fr"


def test_each_engine_gets_its_own_request(credentials):
    chatgpt = build_task("openai", "Prix +20 % : quel outil ?")
    assert chatgpt["keyword"] == "Prix %2B20 %25 : quel outil ?"
    assert chatgpt["location_code"] == 2250 and chatgpt["language_code"] == "fr"
    assert "force_web_search" not in chatgpt
    assert build_task("google_ai_overview", PROMPT)["load_async_ai_overview"] is True
    assert "load_async_ai_overview" not in build_task("google_ai_mode", PROMPT)
    claude = build_task("claude", PROMPT)
    assert claude["model_name"] == credentials.claude_model and claude["web_search"] is True
    assert claude["web_search_country_iso_code"] == "FR"
    assert "web_search" not in build_task("perplexity", PROMPT)


def test_chatgpt_answer_and_cited_sources(credentials):
    result = {
        "model": "gpt-5",
        "markdown": "Pour la CX aux Pays-Bas, TCXA et Mirabeau reviennent souvent.",
        "sources": [
            {"type": "chat_gpt_source", "title": "Top CX bureaus", "url": "https://sortlist.com/cx", "domain": "sortlist.com"},
            {"type": "chat_gpt_source", "title": "Doublon", "url": "https://sortlist.com/cx", "domain": "sortlist.com"},
        ],
        "search_results": [{"url": "https://non-cite.example"}],
    }
    seen = []
    answer = asyncio.run(ask("openai", PROMPT, _client(_envelope(result), seen)))
    assert answer.text.startswith("Pour la CX")
    assert [item.url for item in answer.sources] == ["https://sortlist.com/cx"]
    assert answer.model == "gpt-5" and not answer.no_answer
    request = seen[0]
    assert request.url.path == "/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"
    assert request.headers["authorization"] == "Basic " + base64.b64encode(b"login@test:secret-pass").decode()
    assert json.loads(request.content)[0]["language_code"] == "nl"


def test_google_overview_text_and_nested_references(credentials):
    result = {
        "type": "organic",
        "items": [
            {"type": "organic", "url": "https://x.example"},
            {
                "type": "ai_overview",
                "markdown": "Plusieurs bureaux CX sont cités : TCXA, Mirabeau.",
                "references": [{"url": "https://a.example", "title": "A"}],
                "items": [{"type": "ai_overview_element", "references": [{"url": "https://b.example", "source": "B"}]}],
            },
        ],
    }
    answer = asyncio.run(ask("google_ai_overview", PROMPT, _client(_envelope(result), [])))
    assert answer.model == "Google AI Overviews"
    assert [item.url for item in answer.sources] == ["https://a.example", "https://b.example"]
    assert answer.sources[1].title == "B"


def test_google_without_ai_answer_is_not_a_failure(credentials):
    plain_page = {"type": "organic", "items": [{"type": "organic", "url": "https://x.example"}]}
    assert asyncio.run(ask("google_ai_overview", PROMPT, _client(_envelope(plain_page), []))).no_answer
    empty = _envelope(task_code=40102, task_message="No Search Results.")
    assert asyncio.run(ask("google_ai_mode", PROMPT, _client(empty, []))).no_answer


def test_llm_responses_join_sections_and_annotations(credentials):
    result = {
        "model_name": "claude-sonnet-5-5",
        "items": [
            {"type": "reasoning", "sections": [{"type": "summary_text", "text": "ignoré"}]},
            {
                "type": "message",
                "sections": [
                    {"type": "text", "text": "TCXA accompagne les marques.", "annotations": [{"title": "T", "url": "https://t.example"}]},
                    {"type": "text", "text": "Mirabeau aussi.", "annotations": None},
                ],
            },
        ],
    }
    answer = asyncio.run(ask("claude", PROMPT, _client(_envelope(result), [])))
    assert answer.text == "TCXA accompagne les marques.\n\nMirabeau aussi."
    assert [item.url for item in answer.sources] == ["https://t.example"]


def test_refusals_become_readable_errors(credentials, monkeypatch):
    refused = _envelope(task_code=40200, task_message="Payment Required.")
    with pytest.raises(DataForSEOError, match="40200"):
        asyncio.run(ask("openai", PROMPT, _client(refused, [])))

    async def refusing(provider, prompt, client=None):
        raise DataForSEOError("DataForSEO 40104 : Please verify your account before using the API.")

    monkeypatch.setattr(dataforseo, "ask", refusing)
    monkeypatch.setattr(llm, "settings", SimpleNamespace(**credentials.__dict__, provider_mode=lambda p: "live",
                                                         provider_backend=lambda p: "dataforseo"))
    result = asyncio.run(llm.complete("openai", PROMPT, [], "n"))
    assert result.error == "DataForSEO 40104 : Please verify your account before using the API."


def test_no_answer_runs_are_kept_apart():
    now = datetime.now(timezone.utc)
    assert BatchResult("q", "google_ai_overview", "", [], "Google AI Overviews", "live", None, now, no_answer=True).status == "no_answer"
    assert BatchResult("q", "openai", "", [], "gpt-5", "live", "Erreur", now).status == "failed"
    assert BatchResult("q", "openai", "texte", [], "gpt-5", "live", None, now).status == "completed"


def test_dataforseo_takes_over_every_engine_when_configured():
    configured = SimpleNamespace(**{**settings.__dict__, "dataforseo_login": "l", "dataforseo_password": "p"})
    assert all(type(settings).provider_backend(configured, engine) == "dataforseo" for engine in settings.engines)
    bare = SimpleNamespace(**{**settings.__dict__, "dataforseo_login": "", "openai_api_key": "", "gemini_api_key": ""})
    assert type(settings).provider_backend(bare, "openai") is None
    assert type(settings).provider_backend(bare, "claude") is None
