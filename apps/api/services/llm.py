from __future__ import annotations

import random
import re
from dataclasses import dataclass

import httpx

from config import settings
from services.analyzer import Entity, host_of
from services.simulator import Source, simulate_answer

MODELS = {
    "openai": "gpt-4o",
    "perplexity": "agent-fast",
    "gemini": "gemini-3.8-flash",
}


@dataclass(frozen=True)
class ProviderResult:
    text: str
    sources: list[Source]
    model: str
    source_mode: str
    error: str | None = None


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


async def _call_gemini(prompt: str) -> ProviderResult:
    # La clé passe en en-tête : dans l'URL, elle se retrouvait dans les messages d'erreur.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['gemini']}:generateContent"
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
    return ProviderResult(text=text, sources=_dedupe(sources), model=MODELS["gemini"], source_mode="live")


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
        if provider == "openai":
            return await _call_openai(prompt)
        if provider == "perplexity":
            return await _call_perplexity(prompt)
        if provider == "gemini":
            return await _call_gemini(prompt)
        raise ValueError(f"Moteur inconnu : {provider}")
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
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
        message = "Le moteur n'a pas répondu à temps (60 s)."
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
