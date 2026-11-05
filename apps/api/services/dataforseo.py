"""Moteurs interrogés via DataForSEO.

Trois familles d'appels, toutes en « live » (une question, une réponse, jusqu'à 120 s) :
- scraper : la réponse affichée dans l'interface de ChatGPT ou de Gemini, telle qu'un utilisateur la voit ;
- google : le résumé IA de Google, dans la page de résultats (AI Overviews) ou en mode IA (AI Mode) ;
- responses : la réponse de l'API du modèle, avec recherche web (Perplexity, Claude).

Documentation : https://docs.dataforseo.com/v3/ai_optimization/ et https://docs.dataforseo.com/v3/serp/google/
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from config import settings
from services.analyzer import host_of
from services.simulator import Source

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dataforseo.com/v3"
# DataForSEO annonce jusqu'à 120 s par tâche « live ».
TIMEOUT = httpx.Timeout(150.0, connect=10.0)
OK = 20000
# « No Search Results » : la page existe mais ne contient pas de réponse IA pour cette question.
NO_RESULTS = {40102}

ENDPOINTS = {
    "openai": ("scraper", "/ai_optimization/chat_gpt/llm_scraper/live/advanced"),
    "gemini": ("scraper", "/ai_optimization/gemini/llm_scraper/live/advanced"),
    "google_ai_overview": ("google", "/serp/google/organic/live/advanced"),
    "google_ai_mode": ("google", "/serp/google/ai_mode/live/advanced"),
    "perplexity": ("responses", "/ai_optimization/perplexity/llm_responses/live"),
    "claude": ("responses", "/ai_optimization/claude/llm_responses/live"),
}
GOOGLE_MODELS = {"google_ai_overview": "Google AI Overviews", "google_ai_mode": "Google AI Mode"}

# Codes de lieu Google (ISO 3166 numérique + 2000).
LOCATION_CODES = {
    "FR": 2250,
    "BE": 2056,
    "CH": 2756,
    "CA": 2124,
    "LU": 2442,
    "US": 2840,
    "GB": 2826,
    "NL": 2528,
    "DE": 2276,
    "ES": 2724,
    "IT": 2380,
    "SA": 2682,
}

# Mots courts propres à chaque langue : assez pour trancher sur une question d'acheteur.
_LANGUAGE_WORDS = {
    "fr": {"le", "la", "les", "des", "une", "est", "pour", "quel", "quelle", "quels", "quelles", "comment", "avec",
           "dans", "du", "sur", "qui", "notre", "nos", "mon", "meilleur", "meilleure", "meilleurs", "entreprise"},
    "en": {"the", "what", "which", "how", "best", "for", "with", "and", "are", "is", "to", "of", "our", "my", "does",
           "should", "do", "we", "company", "agency", "agencies"},
    "nl": {"het", "een", "welk", "welke", "hoe", "voor", "met", "zijn", "ons", "onze", "kan", "wat", "bureau", "bij",
           "helpen", "beste", "bedrijf"},
    "de": {"der", "die", "das", "und", "wie", "welche", "welcher", "für", "mit", "ist", "ein", "eine", "unser",
           "beste", "unternehmen"},
    "es": {"el", "los", "las", "qué", "cuál", "cuáles", "cómo", "para", "con", "una", "mejor", "mejores", "empresa"},
    "it": {"il", "gli", "che", "quale", "quali", "come", "per", "una", "migliore", "migliori", "azienda"},
}


class DataForSEOError(Exception):
    """Refus de DataForSEO (compte non vérifié, crédit épuisé, paramètre invalide…), message lisible."""


@dataclass(frozen=True)
class EngineAnswer:
    text: str
    sources: list[Source]
    model: str
    # Vrai quand le moteur n'affiche aucune réponse IA pour la question (fréquent pour AI Overviews).
    no_answer: bool = False


def guess_language(text: str) -> str:
    words = re.findall(r"[a-zà-ÿ]+", text.lower())
    scores = {language: sum(1 for word in words if word in vocabulary) for language, vocabulary in _LANGUAGE_WORDS.items()}
    best = max(scores, key=lambda language: scores[language])
    return best if scores[best] > 0 else settings.dataforseo_language


def _keyword(prompt: str) -> str:
    # DataForSEO demande d'encoder ces deux caractères dans les mots-clés.
    return prompt.replace("%", "%25").replace("+", "%2B")


def build_task(provider: str, prompt: str) -> dict:
    family, _path = ENDPOINTS[provider]
    country = settings.dataforseo_country
    location = LOCATION_CODES.get(country, LOCATION_CODES["FR"])
    language = guess_language(prompt)
    if family == "scraper":
        return {"keyword": _keyword(prompt), "location_code": location, "language_code": language}
    if family == "google":
        task = {"keyword": _keyword(prompt), "location_code": location, "language_code": language, "device": "desktop"}
        if provider == "google_ai_overview":
            # Sans ce paramètre, seuls les résumés déjà en cache reviennent. Remboursé si Google n'en affiche pas.
            task["load_async_ai_overview"] = True
        return task
    task = {
        "user_prompt": prompt[:500],
        "model_name": settings.claude_model if provider == "claude" else settings.perplexity_model,
        "web_search_country_iso_code": country,
    }
    if provider == "claude":
        task["web_search"] = True
    return task


async def ask(provider: str, prompt: str, client: httpx.AsyncClient | None = None) -> EngineAnswer:
    family, path = ENDPOINTS[provider]
    body = [build_task(provider, prompt)]
    if client is None:
        async with httpx.AsyncClient(timeout=TIMEOUT) as owned:
            payload = await _post(owned, path, body)
    else:
        payload = await _post(client, path, body)
    result = _first_result(payload)
    if result is None:
        return EngineAnswer(text="", sources=[], model=GOOGLE_MODELS.get(provider, provider), no_answer=True)
    if family == "scraper":
        return parse_scraper(result)
    if family == "google":
        return parse_google(result, provider)
    return parse_responses(result)


async def _post(client: httpx.AsyncClient, path: str, body: list[dict]) -> dict:
    response = await client.post(
        BASE_URL + path,
        json=body,
        auth=(settings.dataforseo_login, settings.dataforseo_password),
    )
    response.raise_for_status()
    payload = response.json()
    logger.info("DataForSEO %s : %s $", path, payload.get("cost"))
    return payload


def _first_result(payload: dict) -> dict | None:
    """Le premier résultat de la première tâche, None si DataForSEO n'a rien trouvé. Lève sur un refus."""
    if payload.get("status_code") != OK:
        raise DataForSEOError(f"DataForSEO {payload.get('status_code')} : {payload.get('status_message')}")
    task = (payload.get("tasks") or [{}])[0]
    code = task.get("status_code")
    if code in NO_RESULTS:
        return None
    if code != OK:
        raise DataForSEOError(f"DataForSEO {code} : {task.get('status_message')}")
    results = task.get("result") or []
    return results[0] if results else None


def _sources(items: list[dict] | None) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for item in items or []:
        url = (item or {}).get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append(Source(url=url, title=item.get("title") or item.get("source") or host_of(url)))
    return sources


def parse_scraper(result: dict) -> EngineAnswer:
    """ChatGPT et Gemini : la réponse de l'interface et les sources qu'elle cite."""
    text = result.get("markdown") or "\n\n".join(item.get("markdown") or "" for item in result.get("items") or [])
    model = str(result.get("model") or "")
    return EngineAnswer(text=text.strip(), sources=_sources(result.get("sources")), model=model, no_answer=not text.strip())


def parse_google(result: dict, provider: str) -> EngineAnswer:
    """AI Overviews et AI Mode : l'élément « ai_overview » de la page, et ses références."""
    model = GOOGLE_MODELS[provider]
    overview = next((item for item in result.get("items") or [] if item.get("type") == "ai_overview"), None)
    if overview is None:
        return EngineAnswer(text="", sources=[], model=model, no_answer=True)
    elements = overview.get("items") or []
    text = overview.get("markdown") or "\n\n".join(item.get("markdown") or item.get("text") or "" for item in elements)
    references = list(overview.get("references") or [])
    for element in elements:
        references.extend(element.get("references") or [])
    return EngineAnswer(text=text.strip(), sources=_sources(references), model=model, no_answer=not text.strip())


def parse_responses(result: dict) -> EngineAnswer:
    """Perplexity et Claude : le texte du message et les sources qu'il annote."""
    parts: list[str] = []
    annotations: list[dict] = []
    for item in result.get("items") or []:
        if item.get("type") != "message":
            continue
        for section in item.get("sections") or []:
            if section.get("type") == "text" and section.get("text"):
                parts.append(section["text"])
                annotations.extend(section.get("annotations") or [])
    text = "\n\n".join(parts).strip()
    model = str(result.get("model_name") or "")
    return EngineAnswer(text=text, sources=_sources(annotations), model=model, no_answer=not text)
