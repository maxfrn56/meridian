"""Analyse des réponses par Claude. Aucun appel réel : un faux client renvoie la sortie structurée."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import anthropic
import httpx2

import services.orchestrator
from services.analyzer import AnalyzedMention, Entity, mentions_from_analysis
from services.metrics import market_rivals
from services.llm_analysis import BrandMention, ResponseAnalysis, analyze_response, analyze_runs, clean_analysis
from seed import DEMO_EMAIL
from store import store
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

    async def live_batch(jobs, entities):
        now = datetime.now(timezone.utc)
        return [(qid, provider, ANSWER, [], "gpt-4o", "live", None, now) for qid, _prompt, provider in jobs]

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

    run = next(item for item in response.json()["queries"] if item["id"] == query_id)["runs"]["openai"]
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
    assert stored.analysis_version.endswith("/v1")
    assert [item.name for item in stored.analysis] == ["Lumenboard", "Northwind", "Datadash"]

    workspace = store.workspace_for(store.user_by_email(DEMO_EMAIL).id)
    datadash = next(item for item in market_rivals(workspace) if item.name == "Datadash")
    assert (datadash.domain, datadash.mentions, datadash.providers) == ("datadash.com", 2, ("openai",))
