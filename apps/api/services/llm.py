from __future__ import annotations

import random
import re
from dataclasses import dataclass

import httpx

from config import settings
from services import dataforseo
from services.analyzer import Entity, host_of
from services.dataforseo import DataForSEOError
from services.simulator import Source, simulate_answer

# Modèles des appels directs et des simulations. Via DataForSEO, le modèle vient de la réponse.
MODELS = {
    "openai": "gpt-4o",
    "perplexity": "agent-fast",
    "gemini": "gemini-3.8-flash",
    "google_ai_overview": "Google AI Overviews",
    "google_ai_mode": "Google AI Mode",
    "claude": "claude-haiku-5-5",
    "aistudio": "gemini-2.5-flash",
}


class EngineUnavailable(ValueError):
    """Ni DataForSEO ni clé directe pour ce moteur, alors que la simulation est désactivée."""


@dataclass(frozen=True)
class ProviderResult:
    text: str
    sources: list[Source]
    model: str
    source_mode: str
    error: str | None = None
    # Le moteur n'affiche aucune réponse IA pour cette question (AI Overviews le fait souvent).
    no_answer: bool = False


def _mock(prompt: str, provider: str, entities: list[Entity], nonce: str) -> ProviderResult:
    rng = random.Random(f"{provider}|{prompt}|{nonce}")
    text, sources = simulate_answer(prompt, provider, entities, rng, week_index=7)
    return ProviderResult(text=text, sources=sources, model=MODELS[provider], source_mode="mock")


def _openai_sources(payload: dict) -> list[Source]:
    sources: list[Source] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            for annotation in content.get("annotations", []) or []:
                url = annotation.get("url")
                if url:
                    sources.append(Source(url=url, title=annotation.get("title") or host_of(url)))
    return _dedupe(sources)


def _output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts)


async def _call_openai(prompt: str) -> ProviderResult:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": MODELS["openai"],
                "tools": [{"type": "web_search"}],
                # La question part telle quelle, sans consigne : on mesure ce qu'un utilisateur verrait.
                "input": prompt,
            },
        )
        response.raise_for_status()
        payload = response.json()
    return ProviderResult(
        text=_output_text(payload),
        sources=_openai_sources(payload),
        model=MODELS["openai"],
        source_mode="live",
    )


def _perplexity_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts)


def _perplexity_sources(payload: dict) -> list[Source]:
    sources: list[Source] = []
    for item in payload.get("output") or []:
        if item.get("type") != "search_results":
            continue
        for result in item.get("results") or []:
            url = result.get("url")
            if url:
                sources.append(Source(url=url, title=result.get("title") or host_of(url)))
    return _dedupe(sources)


async def _call_perplexity(prompt: str) -> ProviderResult:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.perplexity.ai/v1/agent",
            headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
            json={
                "effort": "fast",
                "input": prompt,
            },
        )
        response.raise_for_status()
        payload = response.json()
    return ProviderResult(
        text=_perplexity_text(payload),
        sources=_perplexity_sources(payload),
        model=str(payload.get("model") or MODELS["perplexity"]),
        source_mode="live",
    )


async def _call_gemini(prompt: str, model: str) -> ProviderResult:
    # La clé passe en en-tête : dans l'URL, elle se retrouvait dans les messages d'erreur.
    # Google AI Studio utilise la même API, avec son propre modèle.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers={"x-goog-api-key": settings.gemini_api_key},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
            },
        )
        response.raise_for_status()
        payload = response.json()
    candidate = payload["candidates"][0]
    parts = candidate.get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
    sources: list[Source] = []
    for chunk in candidate.get("groundingMetadata", {}).get("groundingChunks", []) or []:
        web = chunk.get("web") or {}
        if web.get("uri"):
            sources.append(Source(url=web["uri"], title=web.get("title") or host_of(web["uri"])))
    return ProviderResult(text=text, sources=_dedupe(sources), model=model, source_mode="live")


async def _call_claude(prompt: str) -> ProviderResult:
    model = settings.analysis_model or MODELS["claude"]
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 2048,
                "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
    texts: list[str] = []
    sources: list[Source] = []
    for block in payload.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            texts.append(str(block["text"]))
            for citation in block.get("citations") or []:
                if isinstance(citation, dict) and citation.get("url"):
                    sources.append(Source(url=citation["url"], title=citation.get("title") or host_of(citation["url"])))
        if block.get("type") == "web_search_tool_result":
            for item in block.get("content") or []:
                if isinstance(item, dict) and item.get("url"):
                    sources.append(Source(url=item["url"], title=item.get("title") or host_of(item["url"])))
    return ProviderResult(text="\n".join(texts), sources=_dedupe(sources), model=model, source_mode="live")


def _dedupe(sources: list[Source]) -> list[Source]:
    seen: set[str] = set()
    unique: list[Source] = []
    for source in sources:
        if source.url in seen:
            continue
        seen.add(source.url)
        unique.append(source)
    return unique


async def complete(provider: str, prompt: str, entities: list[Entity], nonce: str) -> ProviderResult:
    mode = settings.provider_mode(provider)
    if mode == "mock":
        return _mock(prompt, provider, entities, nonce)
    try:
        if settings.provider_backend(provider) == "dataforseo":
            answer = await dataforseo.ask(provider, prompt)
            return ProviderResult(
                text=answer.text,
                sources=answer.sources,
                model=answer.model or MODELS.get(provider, provider),
                source_mode="live",
                no_answer=answer.no_answer,
            )
        if provider == "openai":
            return await _call_openai(prompt)
        if provider == "perplexity":
            return await _call_perplexity(prompt)
        if provider == "gemini":
            return await _call_gemini(prompt, MODELS["gemini"])
        if provider == "aistudio":
            return await _call_gemini(prompt, MODELS["aistudio"])
        if provider == "claude":
            return await _call_claude(prompt)
        raise EngineUnavailable("Aucun accès configuré pour ce moteur : ajoutez les identifiants DataForSEO.")
    except (httpx.HTTPError, KeyError, IndexError, ValueError, DataForSEOError) as error:
        return ProviderResult(
            text="",
            sources=[],
            model=MODELS.get(provider, provider),
            source_mode="live",
            error=describe_error(error),
        )


_KEY_PARAM = re.compile(r"(key=)[^&\s'\"]+", re.IGNORECASE)
_KEY_TOKEN = re.compile(r"\b(?:sk|pplx|AIza)[-_A-Za-z0-9]{8,}")
STATUS_LABELS = {
    400: "requête refusée",
    401: "clé refusée",
    403: "accès refusé",
    404: "modèle ou adresse introuvable",
    429: "quota ou limite de débit atteint",
}


def redact_secrets(text: str) -> str:
    """Masque les clés d'API : les erreurs sont affichées au client."""
    return _KEY_TOKEN.sub("•••", _KEY_PARAM.sub(r"\1•••", text))


def describe_error(error: Exception) -> str:
    """Une phrase lisible pour le tableau de bord, sans URL ni clé."""
    if isinstance(error, httpx.TimeoutException):
        message = "Le moteur n'a pas répondu à temps."
    elif isinstance(error, (DataForSEOError, EngineUnavailable)):
        message = str(error)
    elif isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        message = f"Erreur {status} ({STATUS_LABELS.get(status, 'erreur du moteur')})"
        detail = _error_detail(error.response)
        if detail:
            message += f" : {detail}"
    elif isinstance(error, httpx.HTTPError):
        message = f"Connexion au moteur impossible ({error.__class__.__name__})."
    else:
        message = "Réponse du moteur sans contenu exploitable."
    return redact_secrets(message)[:500]


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "").strip()[:300]
    if isinstance(error, str):
        return error.strip()[:300]
    return str(body.get("detail") or "").strip()[:300]
