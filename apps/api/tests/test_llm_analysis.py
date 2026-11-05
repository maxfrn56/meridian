"""Analyse des réponses par Claude. Aucun appel réel : un faux client renvoie la sortie structurée."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import anthropic
import httpx as httpx2

import services.orchestrator
from services.analyzer import AnalyzedMention, Citation, Entity, is_generic_platform, mentions_from_analysis
from services.metrics import domain_gaps, market_rivals
from services.tracker import BatchResult
from services.llm_analysis import BrandMention, ResponseAnalysis, analyze_response, analyze_runs, clean_analysis
from seed import DEMO_EMAIL
from store import Query, StoredRun, Workspace, store
from tests.test_api import _token, client  # noqa: F401  (fixture)

BRAND = Entity("Northwind", "northwind.io", "brand")
RIVAL = Entity("Lumenboard", "lumenboard.com", "competitor")

ANSWER = (
    "Pour une PME, Lumenboard est le choix le plus cité. "
    "Northwind (northwind.io) n'est pas très fiable selon plusieurs avis. "
    "Datadash convient aux grandes équipes."
)


def _brand(name, position, stance, sentiment, excerpt, domain=""):
    return BrandMention(
        name=name, domain=domain, position=position, stance=stance, sentiment=sentiment, excerpt=excerpt
    )


PARSED = ResponseAnalysis(
    brands=[
        _brand("Lumenboard", 1, "recommended", 0.8, "Lumenboard est le choix le plus cité."),
        _brand("NorthWind", 2, "discouraged", -0.6, "Northwind (northwind.io) n'est pas très fiable"),
        _brand("Acme", 3, "recommended", 0.9, "Acme est excellent pour les PME."),
        _brand("Datadash", 4, "compared", 0.2, "Datadash convient aux grandes équipes.", "https://www.datadash.com"),
    ]
)


class FakeMessages:
    def __init__(self, parsed=None, error=None, stop_reason="end_turn"):
        self.parsed, self.error, self.stop_reason = parsed, error, stop_reason
        self.calls = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=self.parsed)


class FakeClient:
    def __init__(self, **kwargs):
        self.messages = FakeMessages(**kwargs)


def test_invented_excerpts_are_dropped_and_ranks_renumbered():
    mentions = clean_analysis(PARSED, ANSWER, [BRAND, RIVAL])
    assert [item.name for item in mentions] == ["Lumenboard", "Northwind", "Datadash"]
    assert [item.position for item in mentions] == [1, 2, 3]
    northwind = mentions[1]
    assert northwind.domain == "northwind.io"
    assert northwind.stance == "discouraged"
    assert northwind.sentiment == -0.6
    assert mentions[2].domain == "datadash.com"


def test_name_variants_map_to_the_tracked_brand_and_values_are_bounded():
    tracked = Entity("Méridien", "meridien.fr", "brand")
    parsed = ResponseAnalysis(brands=[_brand("meridien", 1, "recommended", 1.7, "meridien est très complet")])
    mentions = clean_analysis(parsed, "Selon nous, meridien est très complet.", [tracked])
    assert mentions[0].name == "Méridien"
    assert mentions[0].sentiment == 1.0


def test_stored_analysis_keeps_tracked_brands_and_their_rank():
    analyzed = [
        AnalyzedMention("Datadash", "datadash.com", 1, "recommended", 0.7, "Datadash convient aux grandes équipes."),
        AnalyzedMention("Northwind", "northwind.io", 2, "discouraged", -0.6, "Northwind (northwind.io) n'est pas"),
    ]
    mentions = mentions_from_analysis(ANSWER, analyzed, [BRAND, RIVAL])
    assert [(item.entity_name, item.position, item.stance) for item in mentions] == [("Northwind", 2, "discouraged")]
    assert mentions[0].char_index == ANSWER.index("Northwind")


def test_request_uses_low_effort_and_structured_output():
    fake = FakeClient(parsed=PARSED)
    result = asyncio.run(analyze_response(fake, ANSWER, [BRAND, RIVAL], []))
    assert result is not None and len(result) == 3
    call = fake.messages.calls[0]
    assert call["output_format"] is ResponseAnalysis
    assert call["output_config"] == {"effort": "low"}
    assert "<reponse>" in call["messages"][0]["content"]


def test_failed_or_incomplete_analysis_falls_back():
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    assert asyncio.run(analyze_response(FakeClient(error=error), ANSWER, [BRAND], [])) is None
    truncated = FakeClient(parsed=None, stop_reason="max_tokens")
    assert asyncio.run(analyze_response(truncated, ANSWER, [BRAND], [])) is None


def test_simulated_answers_are_not_sent_to_claude():
    run = SimpleNamespace(id="r1", status="completed", source="mock", response_text=ANSWER, citations=[])
    fake = FakeClient(parsed=PARSED)
    assert asyncio.run(analyze_runs([run], [BRAND], client=fake)) == {}
    assert fake.messages.calls == []


def test_tracking_stores_the_analysis_and_metrics_use_it(client, monkeypatch):  # noqa: F811
    headers = {"Authorization": f"Bearer {_token(client)}"}
    query_id = client.get("/api/v1/settings", headers=headers).json()["queries"][0]["id"]

    async def live_batch(jobs, entities, on_done=None, on_result=None):
        now = datetime.now(timezone.utc)
        rows = []
        for qid, prompt, provider in jobs:
            row = BatchResult(qid, provider, ANSWER, [], "gpt-4o", "live", None, now)
            rows.append(row)
            if on_done is not None:
                on_done(provider, prompt)
            if on_result is not None:
                outcome = on_result(row, prompt)
                if hasattr(outcome, "__await__"):
                    await outcome
        return rows

    fake = FakeClient(parsed=PARSED)
    monkeypatch.setattr(services.orchestrator, "execute_batch", live_batch)
    monkeypatch.setattr(
        services.orchestrator,
        "analyze_runs",
        lambda runs, entities: analyze_runs(runs, entities, client=fake),
    )
    for _ in range(2):
        response = client.post(
            "/api/v1/tracking/run", headers=headers, json={"queryIds": [query_id], "providers": ["openai"]}
        )
        assert response.status_code == 200

    tracking = client.get("/api/v1/tracking", headers=headers)
    assert tracking.status_code == 200
    run = next(item for item in tracking.json()["queries"] if item["id"] == query_id)["runs"]["openai"]
    assert run["analysis"] == "llm"
    assert run["cited"] is True
    assert run["position"] == 2
    # Les mots-clés auraient compté « fiable » comme positif.
    assert run["sentiment"] == -0.6
    assert {item["entityName"]: item["stance"] for item in run["mentions"]} == {
        "Lumenboard": "recommended",
        "Northwind": "discouraged",
    }

    stored = store.workspace_for(store.user_by_email(DEMO_EMAIL).id).runs[-1]
    assert stored.analysis_version.endswith("/v3")
    assert [item.name for item in stored.analysis] == ["Lumenboard", "Northwind", "Datadash"]

    workspace = store.workspace_for(store.user_by_email(DEMO_EMAIL).id)
    datadash = next(item for item in market_rivals(workspace) if item.name == "Datadash")
    assert (datadash.domain, datadash.mentions, datadash.providers) == ("datadash.com", 2, ("openai",))


def test_assistants_and_general_sites_are_not_rivals_or_sources():
    assert is_generic_platform("ChatGPT")
    assert is_generic_platform("OpenAI", "openai.com")
    assert is_generic_platform("Malt", "malt.fr")
    assert is_generic_platform("Codeur.com", "www.codeur.com")
    assert is_generic_platform("Upwork")
    assert not is_generic_platform("Lumenboard", "lumenboard.com")
    assert not is_generic_platform("Atelier Biarritz", "atelier-biarritz.fr")
    now = datetime.now(timezone.utc)
    run = StoredRun(
        id="r",
        query_id="q",
        query_prompt="Quel logiciel à Lyon ?",
        provider="openai",
        model="gpt-4o",
        status="completed",
        source="live",
        response_text="ChatGPT et Lumenboard.",
        citations=[
            Citation("https://openai.com/x", "openai.com", None, 1),
            Citation("https://fr.wikipedia.org/wiki/X", "fr.wikipedia.org", None, 2),
            Citation("https://lumenboard.com/blog", "lumenboard.com", None, 3),
            Citation("https://journal-lyon.fr/logiciel", "journal-lyon.fr", None, 4),
        ],
        error=None,
        created_at=now,
        analysis=[
            AnalyzedMention("Malt", "malt.fr", 1, "recommended", 0.2, "Malt"),
            AnalyzedMention("ChatGPT", "openai.com", 2, "mentioned", 0, "ChatGPT"),
            AnalyzedMention("Lumenboard", "lumenboard.com", 3, "recommended", 0.4, "Lumenboard"),
        ],
    )
    workspace = Workspace(
        id="w",
        user_id="u",
        name="Atelier",
        brand_name="Atelier",
        domain="atelier.fr",
        sector="Logiciel",
        queries=[Query(id="q", prompt="Quel logiciel à Lyon ?", active=True)],
        runs=[run],
    )
    assert [item.name for item in market_rivals(workspace)] == ["Lumenboard"]
    domains = [item.domain for item in domain_gaps(workspace)]
    assert domains == ["journal-lyon.fr"]


def test_rivals_ignore_questions_past_the_daily_allowance():
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    queries = [Query(id=f"q{index}", prompt=f"Question {index} pour le suivi", active=True) for index in range(11)]
    first = StoredRun(
        id="first",
        query_id="q0",
        query_prompt=queries[0].prompt,
        provider="openai",
        model="gpt-4o",
        status="completed",
        source="live",
        response_text="Lumenboard.",
        citations=[],
        error=None,
        created_at=now,
        analysis=[AnalyzedMention("Lumenboard", "lumenboard.com", 1, "recommended", 0.4, "Lumenboard")],
    )
    last = StoredRun(
        id="last",
        query_id="q10",
        query_prompt=queries[10].prompt,
        provider="openai",
        model="gpt-4o",
        status="completed",
        source="live",
        response_text="Agence Oubliee.",
        citations=[],
        error=None,
        created_at=now,
        analysis=[AnalyzedMention("Agence Oubliee", "oubliee.fr", 1, "recommended", 0.4, "Agence Oubliee")],
    )
    workspace = Workspace(
        id="w",
        user_id="u",
        name="Atelier",
        brand_name="Atelier",
        domain="atelier.fr",
        sector="Logiciel",
        queries=queries,
        runs=[first, last],
        trial_ends_at=now + timedelta(days=3),
    )
    assert [item.name for item in market_rivals(workspace)] == ["Lumenboard"]
