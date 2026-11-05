"""Génération des questions par Claude. Aucun appel réel : faux client et site factice."""

from types import SimpleNamespace

import routers.settings
import services.prompt_generator as generator
from config import settings
from services.prompt_generator import (
    GeneratedQuestions,
    SitePortrait,
    clean_questions,
    generate_questions,
    page_brief,
    question_budget,
)
from tests.test_api import _token, client  # noqa: F401  (fixture)


class FakeMessages:
    def __init__(self, questions):
        self.questions = questions
        self.calls = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("output_format") is SitePortrait:
            parsed = SitePortrait(
                activity="analyse produit pour une scale-up",
                size="éditeur",
                reach="non précisée",
                places=[],
                peers="éditeurs d'analytics produit",
            )
        else:
            parsed = GeneratedQuestions(questions=self.questions)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=parsed)


class FakeClient:
    def __init__(self, questions):
        self.messages = FakeMessages(questions)


def test_questions_stay_on_the_city_when_one_is_known():
    raw = [
        "Quel logiciel de suivi choisir ?",
        "Quel logiciel de suivi choisir à Lyon ?",
        "Comment ChatGPT aide une entreprise à Lyon ?",
    ]
    kept = clean_questions(raw, "Atelier", "atelier.fr", [], 5, "Logiciel · France, Lyon, plusieurs pays")
    assert kept == ["Quel logiciel de suivi choisir à Lyon ?"]


def test_budget_follows_the_plan():
    assert question_budget("essentiel", 0) == 20
    assert question_budget("croissance", 12) == 88
    assert question_budget("reference", 0) == 200
    assert question_budget("reference", 250) == 0
    # Sans forfait : l'essai, dix questions par jour.
    assert question_budget(None, 0) == 10
    from datetime import datetime, timedelta, timezone

    assert question_budget(None, 0, datetime.now(timezone.utc) - timedelta(days=1)) == 0


def test_questions_stay_on_the_portrait_places_and_drop_directories():
    raw = [
        "Quelles sont les meilleures plateformes de freelances en France ?",
        "Quel développeur web freelance à Biarritz pour une boutique ?",
        "Petite agence web au Pays basque pour un site vitrine ?",
        "Quel développeur web à Paris ?",
    ]
    kept = clean_questions(
        raw,
        "Atelier",
        "atelier.fr",
        [],
        5,
        "Service · France",
        ["biarritz", "pays basque"],
    )
    assert kept == [
        "Quel développeur web freelance à Biarritz pour une boutique ?",
        "Petite agence web au Pays basque pour un site vitrine ?",
    ]


def test_page_brief_keeps_the_area_declared_in_structured_data():
    html = """
    <html><head>
      <title>Développeur freelance</title>
      <meta name="description" content="Sites et e-commerce." />
      <script type="application/ld+json">
        {"areaServed": ["Biarritz", "Pays Basque", "France"], "jobTitle": "Développeur web freelance"}
      </script>
    </head><body><h1>Sites</h1><p>Je conçois des sites.</p></body></html>
    """
    brief = page_brief(html)
    assert "areaServed : Biarritz, Pays Basque, France" in brief
    assert "jobTitle : Développeur web freelance" in brief
    assert "Je conçois des sites." in brief


def test_questions_naming_the_brand_or_repeated_are_dropped():
    raw = [
        "Quelle agence CX choisir pour une PME ?",
        "TCXA est-elle une bonne agence ?",
        "Que vaut tcxa.agency ?",
        "quelle agence cx choisir pour une PME ?",
        "Court ?",
        "Quels cabinets aident à faire remonter un NPS en baisse ?",
    ]
    kept = clean_questions(raw, "TCXA", "tcxa.agency", ["Quels cabinets aident à faire remonter un NPS en baisse ?"], 5)
    assert kept == ["Quelle agence CX choisir pour une PME ?"]


def test_generation_endpoint_proposes_the_plan_budget(client, monkeypatch):  # noqa: F811
    headers = {"Authorization": f"Bearer {_token(client)}"}
    current = client.get("/api/v1/settings", headers=headers).json()
    existing = [item["prompt"] for item in current["queries"]]
    proposals = [f"Quel outil d'analyse produit choisir pour une équipe de taille {index} ?" for index in range(1, 10)]
    fake = FakeClient(["Northwind vaut-il le coup ?", *proposals])

    async def no_site(domain):
        return "Titre : Analyse produit"

    async def with_fake(**kwargs):
        return await generate_questions(**kwargs, client=fake)

    monkeypatch.setattr(generator, "site_summary", no_site)
    monkeypatch.setattr(routers.settings, "generate_questions", with_fake)
    response = client.post(
        "/api/v1/settings/queries/generate",
        headers=headers,
        json={"brandName": "Northwind", "domain": "northwind.io", "sector": "Product analytics", "existing": existing},
    )
    assert response.status_code == 200
    questions = response.json()["questions"]
    # Forfait Croissance : 100 questions par jour, 12 déjà en place. Le faux n'en propose que neuf.
    assert questions == proposals
    assert [call["output_format"] for call in fake.messages.calls] == [SitePortrait, GeneratedQuestions]
    portrait, questions = fake.messages.calls
    assert "<site>" in portrait["messages"][0]["content"]
    assert "Écris 105 nouvelles questions." in questions["messages"][0]["content"]
    assert "éditeurs d'analytics produit" in questions["messages"][0]["content"]
    assert "analyse produit pour une scale-up" in questions["messages"][0]["content"]
    # Rien n'est enregistré : le client relit avant d'enregistrer.
    assert len(client.get("/api/v1/settings", headers=headers).json()["queries"]) == 12


def test_generation_without_key_says_so(client, monkeypatch):  # noqa: F811
    headers = {"Authorization": f"Bearer {_token(client)}"}
    monkeypatch.setattr(generator, "settings", SimpleNamespace(**{**settings.__dict__, "anthropic_api_key": ""}))
    response = client.post(
        "/api/v1/settings/queries/generate",
        headers=headers,
        json={"brandName": "Northwind", "domain": "northwind.io", "existing": []},
    )
    assert response.status_code == 503
    assert "pas configurée" in response.json()["detail"]


def test_full_list_cannot_grow(client):  # noqa: F811
    headers = {"Authorization": f"Bearer {_token(client)}"}
    existing = [f"Question numéro {index} sur l'analyse produit ?" for index in range(100)]
    response = client.post(
        "/api/v1/settings/queries/generate",
        headers=headers,
        json={"brandName": "Northwind", "domain": "northwind.io", "existing": existing},
    )
    assert response.status_code == 422
