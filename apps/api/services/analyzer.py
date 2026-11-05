from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse

POSITIVE = (
    "recommandé",
    "recommandée",
    "solide",
    "apprécié",
    "appréciée",
    "clair",
    "clarté",
    "fiable",
    "leader",
    "excellent",
    "efficace",
    "robuste",
    "précis",
    "complet",
    "innovant",
    "rapide",
    "lisibilité",
    "trusted",
    "leading",
    "reliable",
    "best",
    "strong",
)
NEGATIVE = (
    "coûteux",
    "couteux",
    "cher",
    "complexe",
    "lent",
    "faible",
    "décevant",
    "problème",
    "manque",
    "fragile",
    "limité",
    "limitee",
    "poor",
    "expensive",
    "slow",
    "weak",
    "missing",
)


@dataclass(frozen=True)
class Entity:
    name: str
    domain: str
    kind: str  # brand | competitor


@dataclass(frozen=True)
class Citation:
    url: str
    domain: str
    title: str | None
    position: int


@dataclass(frozen=True)
class Mention:
    entity_name: str
    entity_type: str
    position: int
    sentiment: float
    excerpt: str
    char_index: int
    stance: str | None = None  # renseigné seulement par l'analyse LLM


STANCES = ("recommended", "compared", "mentioned", "discouraged")


@dataclass(frozen=True)
class AnalyzedMention:
    """Marque relevée par l'analyse LLM, telle qu'enregistrée en base.

    Toutes les marques nommées sont gardées, suivies ou non : la liste des concurrents
    peut changer après coup, le rapprochement avec les marques suivies se fait à la lecture.
    """

    name: str
    domain: str
    position: int
    stance: str
    sentiment: float
    excerpt: str


def host_of(url: str) -> str:
    raw = urlparse(url).netloc.lower()
    if "@" in raw:
        raw = raw.split("@")[-1]
    if ":" in raw:
        raw = raw.split(":")[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def normalize_domain(value: str) -> str:
    text = value.strip().lower()
    if "://" in text:
        text = host_of(text)
    text = text.split("/")[0]
    if text.startswith("www."):
        text = text[4:]
    return text


def _spans(text: str, needle: str) -> list[int]:
    if not needle:
        return []
    pattern = re.compile(rf"(?<!\w){re.escape(needle)}(?!\w)", re.IGNORECASE)
    return [match.start() for match in pattern.finditer(text)]


def _sentiment(text: str, start: int, end: int) -> float:
    snippet = text[start:end].lower()
    positive = sum(1 for word in POSITIVE if word in snippet)
    negative = sum(1 for word in NEGATIVE if word in snippet)
    if positive + negative == 0:
        return 0.0
    return round((positive - negative) / (positive + negative), 2)


def _excerpt(text: str, index: int, span: int = 110) -> str:
    start = max(0, index - span)
    end = min(len(text), index + span)
    chunk = " ".join(text[start:end].split())
    if start > 0:
        chunk = f"…{chunk}"
    if end < len(text):
        chunk = f"{chunk}…"
    return chunk


def extract_mentions(text: str, entities: list[Entity]) -> list[Mention]:
    found: list[tuple[int, Entity]] = []
    for entity in entities:
        indexes = _spans(text, entity.name) + _spans(text, entity.domain)
        if indexes:
            found.append((min(indexes), entity))
    found.sort(key=lambda item: (item[0], item[1].name.lower()))
    mentions: list[Mention] = []
    for position, (index, entity) in enumerate(found, start=1):
        # Le score s'arrête à la prochaine marque pour ne pas mélanger deux jugements.
        end = found[position][0] if position < len(found) else min(len(text), index + 220)
        mentions.append(
            Mention(
                entity_name=entity.name,
                entity_type=entity.kind,
                position=position,
                sentiment=_sentiment(text, index, end),
                excerpt=_excerpt(text, index),
                char_index=index,
            )
        )
    return mentions


def fold(value: str) -> str:
    """Casse et accents ignorés : « Méridien » et « meridien » se valent."""
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).casefold().split())


# Assistants qui répondent, et plateformes citées comme source générale : pas des concurrents du client.
_GENERIC_NAMES = {
    "chatgpt",
    "chat gpt",
    "openai",
    "gpt4",
    "gpt4o",
    "gpt-4",
    "gpt-4o",
    "perplexity",
    "gemini",
    "google gemini",
    "bard",
    "claude",
    "anthropic",
    "copilot",
    "microsoft copilot",
    "meta ai",
    "google",
    "bing",
    "wikipedia",
    "wikipédia",
    "youtube",
    "linkedin",
    "facebook",
    "instagram",
    "twitter",
    "reddit",
    "tiktok",
    # Places de marché et annuaires de prestataires : ils recensent des concurrents, ils n'en sont pas.
    "malt",
    "codeur",
    "codeur.com",
    "upwork",
    "fiverr",
    "comeup",
    "come up",
    "5euros",
    "5 euros",
    "5euros.com",
    "peopleperhour",
    "people per hour",
    "toptal",
    "sortlist",
    "goodfirms",
    "designrush",
    "design rush",
    "lehibou",
    "le hibou",
    "kicklox",
    "creme de la creme",
}
_GENERIC_DOMAINS = {
    "openai.com",
    "chatgpt.com",
    "perplexity.ai",
    "gemini.google.com",
    "bard.google.com",
    "anthropic.com",
    "claude.ai",
    "wikipedia.org",
    "wikimedia.org",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "tiktok.com",
    "google.com",
    "bing.com",
    "malt.fr",
    "malt.com",
    "codeur.com",
    "upwork.com",
    "fiverr.com",
    "freelancer.com",
    "comeup.com",
    "5euros.com",
    "peopleperhour.com",
    "toptal.com",
    "sortlist.com",
    "sortlist.fr",
    "clutch.co",
    "goodfirms.co",
    "designrush.com",
    "comet.co",
    "lehibou.com",
    "kicklox.com",
    "cremedelacreme.io",
}


def is_generic_platform(name: str, domain: str = "") -> bool:
    """Vrai pour un assistant ou un site général, qui n'est pas un concurrent métier."""
    compact = fold(name).replace("-", "").replace(" ", "")
    spaced = fold(name)
    if spaced in _GENERIC_NAMES or compact in {item.replace("-", "").replace(" ", "") for item in _GENERIC_NAMES}:
        return True
    host = normalize_domain(domain)
    if host.startswith("www."):
        host = host[4:]
    return any(host == item or host.endswith(f".{item}") for item in _GENERIC_DOMAINS if host)


def locate(excerpt: str, text: str) -> int | None:
    """Position de l'extrait dans la réponse, None s'il n'y figure pas.

    Sert de garde-fou : un extrait introuvable veut dire que le modèle a reformulé ou inventé.
    """
    words = excerpt.strip().strip("…\"'«» ").split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.search(pattern, text, re.IGNORECASE)
    return match.start() if match else None


def matching_entity(name: str, domain: str, entities: list[Entity]) -> Entity | None:
    folded = fold(name)
    owned = normalize_domain(domain) if domain else ""
    for entity in entities:
        if folded and folded == fold(entity.name):
            return entity
        tracked = normalize_domain(entity.domain) if entity.domain else ""
        if owned and tracked and (owned == tracked or owned.endswith(f".{tracked}")):
            return entity
    return None


def mentions_from_analysis(text: str, analyzed: list[AnalyzedMention], entities: list[Entity]) -> list[Mention]:
    """Mentions des marques suivies, à partir de l'analyse LLM enregistrée.

    Le rang ignore les annuaires et les assistants : Malt en tête ne décale pas une agence.
    """
    visible: list[tuple[Entity | None, AnalyzedMention]] = []
    for item in sorted(analyzed, key=lambda value: value.position):
        entity = matching_entity(item.name, item.domain, entities)
        if entity is None and is_generic_platform(item.name, item.domain):
            continue
        visible.append((entity, item))
    mentions: list[Mention] = []
    seen: set[str] = set()
    for rank, (entity, item) in enumerate(visible, start=1):
        if entity is None or entity.name in seen:
            continue
        seen.add(entity.name)
        index = locate(item.excerpt, text)
        mentions.append(
            Mention(
                entity_name=entity.name,
                entity_type=entity.kind,
                position=rank,
                sentiment=item.sentiment,
                excerpt=item.excerpt,
                char_index=index if index is not None else 0,
                stance=item.stance,
            )
        )
    return mentions


def brand_is_cited(mentions: list[Mention], citations: list[Citation], brand: Entity) -> bool:
    if any(item.entity_type == "brand" and item.entity_name == brand.name for item in mentions):
        return True
    domain = normalize_domain(brand.domain)
    return any(item.domain == domain or item.domain.endswith(f".{domain}") for item in citations)


def share_of_voice(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {name: 0.0 for name in counts}
    return {name: value / total for name, value in counts.items()}


def citation_rate(flags: list[bool]) -> float | None:
    if not flags:
        return None
    return sum(1 for flag in flags if flag) / len(flags)


# Marques écrites comme dans une réponse de moteur : « Amplitude (amplitude.com) ».
_NAMED_ORG = re.compile(
    r"\b([A-Z][A-Za-z0-9][A-Za-z0-9&.'’+-]{1,40}(?:\s+[A-Z][A-Za-z0-9][A-Za-z0-9&.'’+-]{1,40}){0,2})"
    r"\s+\(([a-z0-9.-]+\.[a-z]{2,})\)"
)


def named_organisations(text: str) -> list[tuple[str, str]]:
    """Retourne les couples (nom, domaine) cités explicitement dans une réponse."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in _NAMED_ORG.finditer(text):
        name = " ".join(match.group(1).split())
        domain = normalize_domain(match.group(2))
        if domain in seen:
            continue
        seen.add(domain)
        found.append((name, domain))
    return found
