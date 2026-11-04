from __future__ import annotations

import re
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
