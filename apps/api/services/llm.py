from __future__ import annotations

import random
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
                "instructions": (
                    "Tu réponds en français, de façon comparative et sourcée. "
                    "N'avantage aucune marque qui ne serait pas étayée par les sources."
                ),
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
                "input": "Réponds en français, cite tes sources, sans favoriser une marque a priori.\n\n" + prompt,
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
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODELS['gemini']}:generateContent?key={settings.gemini_api_key}"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
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
        message = str(error).strip() or error.__class__.__name__
        return ProviderResult(
            text="",
            sources=[],
            model=MODELS.get(provider, provider),
            source_mode="live",
            error=message[:500],
        )
