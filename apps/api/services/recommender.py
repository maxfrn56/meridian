from __future__ import annotations

from dataclasses import dataclass

from services.auditor import SCHEMA_TYPES, AuditDraft

PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}


@dataclass(frozen=True)
class DomainGap:
    domain: str
    citations: int
    runs_without_brand: int


@dataclass(frozen=True)
class Recommendation:
    id: str
    priority: str
    category: str
    title: str
    detail: str
    effort: str
    steps: tuple[str, ...] = ()


def build_recommendations(
    audit: AuditDraft,
    gaps: list[DomainGap],
    discovered_names: list[str] | None = None,
) -> list[Recommendation]:
    items: list[Recommendation] = []
    if not audit.llms_txt:
        items.append(
            Recommendation(
                id="llms-txt",
                priority="P1",
                category="technical",
                title="Publier un fichier llms.txt",
                detail="Les moteurs n'ont pas de mode d'emploi de votre site. Ce fichier le leur donne.",
                effort="low",
                steps=(
                    "Créez un fichier texte nommé llms.txt.",
                    "Mettez-le à la racine du site, pour qu'il s'ouvre à https://votre-domaine/llms.txt.",
                    "Écrivez en une phrase qui vous êtes, puis listez les 5 à 10 pages à citer.",
                    "Ajoutez le lien de votre page FAQ et de vos pages de comparaison.",
                    "Relancez l'audit : la ligne « Fichier llms.txt » doit passer au vert.",
                ),
            )
        )
    for bot, status in audit.bots.items():
        if status == "disallowed":
            items.append(
                Recommendation(
                    id=f"allow-{bot.lower()}",
                    priority="P1",
                    category="technical",
                    title=f"Autoriser {bot} dans robots.txt",
                    detail=f"{bot} n'a pas le droit de lire le site, donc il ne peut pas vous citer.",
                    effort="low",
                    steps=(
                        "Ouvrez le fichier robots.txt à la racine du site.",
                        f"Trouvez le bloc User-agent: {bot}.",
                        "Supprimez la ligne Disallow: / de ce bloc, ou remplacez-la par Allow: /.",
                        "Publiez le fichier, puis relancez l'audit.",
                    ),
                )
            )
    missing = [name for name in SCHEMA_TYPES if name not in audit.found_schema_types]
    for name in missing:
        priority = "P1" if name == "Organization" else "P2"
        category = "technical" if name in {"Organization", "Product", "Article"} else "semantic"
        items.append(
            Recommendation(
                id=f"schema-{name.lower()}",
                priority=priority,
                category=category,
                title=f"Ajouter le schéma JSON-LD {name}",
                detail=_schema_detail(name),
                effort="medium" if name != "Organization" else "low",
                steps=_schema_steps(name),
            )
        )
    if audit.heading_score < 70:
        items.append(
            Recommendation(
                id="question-headings",
                priority="P2",
                category="semantic",
                title="Reformuler les H2 et H3 en questions",
                detail="Un moteur reprend plus facilement un titre qui est déjà la question de l'internaute.",
                effort="medium",
                steps=(
                    "Reprenez chaque H2 et H3 qui n'est pas une question.",
                    "Réécrivez-le comme la demandent vos clients : « Comment… », « Quel… », « Pourquoi… ».",
                    "Juste sous le titre, répondez en 40 à 80 mots, sans renvoyer vers une autre page.",
                    "Gardez le même sujet : seule la formulation change.",
                ),
            )
        )
    if audit.factual_score < 70:
        items.append(
            Recommendation(
                id="factual-density",
                priority="P2",
                category="semantic",
                title="Renforcer la densité factuelle",
                detail=f"La page est trop narrative. {audit.factual_detail}",
                effort="medium",
                steps=(
                    "Ajoutez au moins un chiffre sourcé par section importante (pourcentage, délai, prix).",
                    "Remplacez un paragraphe de comparaison par un tableau : vous, puis chaque concurrent, une ligne par critère.",
                    "Terminez les pages longues par une liste à puces de 5 faits vérifiables.",
                ),
            )
        )
    if "FAQPage" in missing:
        items.append(
            Recommendation(
                id="faq-block",
                priority="P2",
                category="semantic",
                title="Ajouter un bloc FAQ aligné sur les requêtes cibles",
                detail="La FAQ est le format le plus simple à reprendre dans une réponse générée.",
                effort="medium",
                steps=(
                    "Choisissez 5 à 8 questions parmi vos requêtes suivies.",
                    "Écrivez sous chaque question une réponse autonome de 40 à 80 mots.",
                    "Balisez ce bloc avec le schéma FAQPage.",
                    "Relancez l'audit pour confirmer que FAQPage est détecté.",
                ),
            )
        )
    for gap in sorted(gaps, key=lambda item: item.runs_without_brand, reverse=True)[:3]:
        if gap.runs_without_brand < 2:
            continue
        items.append(
            Recommendation(
                id=f"authority-{gap.domain.replace('.', '-')}",
                priority="P3",
                category="authority",
                title=f"Obtenir une citation sur {gap.domain}",
                detail=(
                    f"{gap.domain} est cité dans {gap.citations} réponse(s), dont {gap.runs_without_brand} "
                    "où votre marque est absente."
                ),
                effort="high",
                steps=(
                    f"Repérez la page de {gap.domain} que les moteurs citent (comparatif, fiche ou article).",
                    "Proposez une mise à jour sourcée : un chiffre, un cas client, ou une différence factuelle.",
                    "Une fois la page en ligne, relancez le suivi pour voir si votre marque y est associée.",
                ),
            )
        )
    names = [name for name in (discovered_names or []) if name.strip()]
    if names:
        shown = ", ".join(names[:3])
        items.append(
            Recommendation(
                id="unlisted-competitors",
                priority="P2",
                category="authority",
                title="Vous comparer aux marques que les moteurs citent",
                detail=f"Sur vos questions, les moteurs nomment surtout {shown}.",
                effort="medium",
                steps=(
                    "Dans Comparaison, repérez les questions où ces marques sont nommées et pas vous.",
                    "Publiez une page par comparaison (« Vous ou X ») avec un tableau de différences chiffrées.",
                    "Relancez le suivi : votre marque doit apparaître sur les questions où ces noms reviennent.",
                ),
            )
        )
    items.sort(key=lambda item: (PRIORITY_ORDER[item.priority], item.title))
    return _dedupe(items)


def _dedupe(items: list[Recommendation]) -> list[Recommendation]:
    seen: set[str] = set()
    unique: list[Recommendation] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)
    return unique


def _schema_steps(name: str) -> tuple[str, ...]:
    steps = {
        "Organization": (
            "Ajoutez un bloc JSON-LD Organization sur la page d'accueil.",
            "Renseignez le nom exact de la marque, l'URL du site et l'URL du logo.",
            "Ajoutez les profils officiels (LinkedIn, et le reste seulement s'ils existent).",
        ),
        "Product": (
            "Sur la page de l'offre, ajoutez un bloc JSON-LD Product.",
            "Remplissez le nom, une description d'une ou deux phrases, et la catégorie.",
            "Ne mettez un prix que s'il est public et à jour.",
        ),
        "FAQPage": (
            "Reprenez les questions et réponses déjà visibles sur la page.",
            "Encadrez-les avec un bloc JSON-LD de type FAQPage.",
            "Une question du bloc doit correspondre mot pour mot au titre visible.",
        ),
        "Article": (
            "Sur chaque page de fond, ajoutez un bloc JSON-LD Article.",
            "Renseignez le titre, la date de mise à jour et le nom de l'auteur.",
            "La date doit changer quand le texte change : les moteurs préfèrent une source datée.",
        ),
    }
    return steps[name]


def _schema_detail(name: str) -> str:
    details = {
        "Organization": "Déclarez le nom, le domaine, le logo et les profils officiels. C'est l'ancre d'identité que les moteurs rapprochent de la marque.",
        "Product": "Décrivez l'offre (nom, description, catégorie). Sans Product, la page reste un texte marketing difficile à extraire.",
        "FAQPage": "Balisez les questions/réponses déjà visibles. Un FAQPage valide est l'un des formats les plus repris dans les réponses.",
        "Article": "Sur les pages de fond, ajoutez headline, dateModified et auteur. Cela aide le moteur à citer un passage daté plutôt qu'un concurrent.",
    }
    return details[name]
