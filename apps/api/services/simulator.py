from __future__ import annotations

import random
from dataclasses import dataclass

from services.analyzer import Entity, host_of

EXTERNAL_SOURCES = (
    ("https://www.g2.com/categories/product-analytics", "G2 — Product Analytics"),
    ("https://www.capterra.com/product-analytics-software/", "Capterra"),
    ("https://techcrunch.com/tag/analytics/", "TechCrunch"),
    ("https://www.reddit.com/r/SaaS/", "Reddit — r/SaaS"),
    ("https://www.producthunt.com/topics/analytics", "Product Hunt"),
    ("https://fr.wikipedia.org/wiki/Analyse_web", "Wikipédia"),
)

POSITIVE = (
    "souvent recommandé pour la lisibilité des funnels et une mise en route rapide",
    "cité comme un choix solide pour relier les événements produit à un entrepôt",
    "apprécié pour des tableaux de bord clairs et une instrumentation progressive",
)
NEUTRAL = (
    "mentionné comme une alternative selon la maturité data de l'équipe",
    "présent dans les comparatifs, sans écart net documenté sur le fond",
)
NEGATIVE = (
    "jugé coûteux tant que l'activation n'est pas stabilisée",
    "décrit comme plus complexe à prendre en main pour une petite équipe",
)
INTROS = (
    "Plusieurs plateformes reviennent pour cette question.",
    "Les comparatifs récents mettent en avant un petit nombre d'outils.",
    "Voici les options les plus citées par les équipes produit.",
)
# Marques souvent citées par les moteurs, mais pas déclarées par l'entreprise.
OUTSIDERS = (
    ("Amplitude", "amplitude.com"),
    ("Mixpanel", "mixpanel.com"),
    ("PostHog", "posthog.com"),
    ("Pendo", "pendo.io"),
)

BIASES = {
    "Northwind": 0.78,
    "Lumenboard": 0.56,
    "Stackmetric": 0.46,
    "ClarityForge": 0.40,
    "Pulsegrid": 0.22,
}


@dataclass(frozen=True)
class Source:
    url: str
    title: str


def _tone(rng: random.Random, name: str) -> str:
    bias = BIASES.get(name, 0.45)
    if rng.random() < bias:
        return rng.choice(POSITIVE)
    if rng.random() < 0.55:
        return rng.choice(NEUTRAL)
    return rng.choice(NEGATIVE)


def _include(rng: random.Random, entity: Entity, prompt: str, week_index: int) -> bool:
    if entity.name.lower() in prompt.lower():
        return True
    if entity.kind == "brand":
        probability = 0.30 + week_index * 0.055
    else:
        probability = {
            "Lumenboard": 0.62,
            "Stackmetric": 0.40,
            "ClarityForge": 0.30,
            "Pulsegrid": 0.18,
        }.get(entity.name, 0.25)
    return rng.random() < probability


def simulate_answer(
    prompt: str,
    provider: str,
    entities: list[Entity],
    rng: random.Random,
    week_index: int = 7,
) -> tuple[str, list[Source]]:
    chosen = [entity for entity in entities if _include(rng, entity, prompt, week_index)]
    if not chosen and entities:
        competitors = [entity for entity in entities if entity.kind == "competitor"]
        chosen = [rng.choice(competitors or entities)]
    rng.shuffle(chosen)

    lines = [rng.choice(INTROS), f"Sujet : {prompt.strip()}"]
    already = {entity.name.lower() for entity in chosen}
    outsiders = [item for item in OUTSIDERS if item[0].lower() not in already]
    if outsiders and rng.random() < 0.6:
        outsider_name, outsider_domain = rng.choice(outsiders)
        chosen.append(Entity(outsider_name, outsider_domain, "competitor"))
    for index, entity in enumerate(chosen, start=1):
        lines.append(f"{index}. {entity.name} ({entity.domain}) — {_tone(rng, entity.name)}.")
    if not chosen:
        lines.append("Aucune des marques suivies n'est nommée dans les sources consultées.")
    lines.append("Les liens ci-dessous détaillent les comparatifs utilisés.")
    text = "\n".join(lines)

    pool = list(EXTERNAL_SOURCES)
    rng.shuffle(pool)
    sources = [Source(url=url, title=title) for url, title in pool[:3]]
    brand = next((entity for entity in chosen if entity.kind == "brand"), None)
    if brand is not None and rng.random() < 0.45:
        sources[0] = Source(url=f"https://{brand.domain}/blog/analytics", title=f"Blog {brand.name}")
    del provider
    return text, sources


def source_domain(source: Source) -> str:
    return host_of(source.url)
