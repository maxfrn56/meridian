import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app
from seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo
from store import store


@pytest.fixture()
def client():
    previous = settings.mock_llm
    object.__setattr__(settings, "mock_llm", "true")
    store.reset()
    seed_demo(store)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        object.__setattr__(settings, "mock_llm", previous)


def _token(client: TestClient) -> str:
    response = client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert response.status_code == 200
    return response.json()["token"]


def test_login_overview_and_tracking_contract(client: TestClient):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    overview = client.get("/api/v1/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["brandName"] == "Northwind"
    assert body["kpis"]["queriesTracked"] == 12
    assert 0 <= body["kpis"]["geoScore"] <= 100
    assert body["trend"]
    assert body["shareOfVoice"]
    tracking = client.get("/api/v1/tracking", headers=headers)
    assert tracking.status_code == 200
    assert len(tracking.json()["queries"]) == 12
    audit = client.get("/api/v1/audit", headers=headers)
    assert audit.status_code == 200
    assert audit.json()["audit"]["recommendations"]
    discovered = audit.json()["discoveredCompetitors"]
    assert discovered
    declared = {"Northwind", "Lumenboard", "Stackmetric", "ClarityForge", "Pulsegrid"}
    assert all(item["name"] not in declared for item in discovered)
    assert any(item["id"] == "unlisted-competitors" and item["steps"] for item in audit.json()["audit"]["recommendations"])


def test_comparison_ranks_brand_against_competitors(client: TestClient):
    token = _token(client)
    response = client.get("/api/v1/comparison", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["brandName"] == "Northwind"
    assert body["runs"] > 0
    assert body["entities"][0]["name"] == "Northwind"
    assert body["entities"][0]["kind"] == "brand"
    assert {item["name"] for item in body["entities"]} == {
        "Northwind",
        "Lumenboard",
        "Stackmetric",
        "ClarityForge",
        "Pulsegrid",
    }
    assert all(0 <= item["visibility"] <= 1 for item in body["entities"])
    assert all(0 <= item["sourcedRate"] <= 1 for item in body["entities"])
    assert all(0 <= item["ownSourceRate"] <= 1 for item in body["entities"])
    assert body["prompts"]
    assert body["prompts"][0]["cells"]
    assert body["gaps"]
    assert body["providers"]


def test_subscription_limits_questions_sent_this_month(client: TestClient):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    billing = client.get("/api/v1/billing", headers=headers)
    assert billing.status_code == 200
    body = billing.json()
    assert body["plan"]["id"] == "croissance"
    assert body["plan"]["questionsPerMonth"] == 20
    assert len(body["plans"]) == 3
    switched = client.post("/api/v1/billing", headers=headers, json={"planId": "essentiel"})
    assert switched.status_code == 200
    assert switched.json()["questionsRemaining"] == 5
    blocked = client.post("/api/v1/tracking/run", headers=headers, json={})
    assert blocked.status_code == 400
    assert "Essentiel" in blocked.json()["detail"]
    after = client.get("/api/v1/billing", headers=headers).json()
    assert after["questionsUsed"] == 0


def test_settings_reject_a_sixth_competitor(client: TestClient):
    token = _token(client)
    current = client.get("/api/v1/settings", headers={"Authorization": f"Bearer {token}"})
    payload = current.json()
    payload["competitors"].extend(
        [
            {"name": "Extra", "domain": "extra.example"},
            {"name": "Encore", "domain": "encore.example"},
        ]
    )
    response = client.put("/api/v1/settings", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert response.status_code == 422


def test_tracking_run_appends_results(client: TestClient):
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    before = client.get("/api/v1/overview", headers=headers).json()["kpis"]["runsCompleted"]
    settings = client.get("/api/v1/settings", headers=headers).json()
    query_id = settings["queries"][0]["id"]
    response = client.post(
        "/api/v1/tracking/run",
        headers=headers,
        json={"queryIds": [query_id], "providers": ["perplexity"]},
    )
    assert response.status_code == 200
    after = client.get("/api/v1/overview", headers=headers).json()["kpis"]["runsCompleted"]
    assert after == before + 1


def test_prospects_survive_in_their_own_file(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr("services.prospects.PATH", tmp_path / "prospects.json")
    headers = {"Authorization": f"Bearer {_token(client)}"}
    listing = client.get("/api/v1/prospects", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["items"][0]["email"] == "contact@pure-nat.com"
    created = client.post(
        "/api/v1/prospects",
        headers=headers,
        json={"company": "Notox", "city": "Anglet", "status": "a_contacter", "channel": "linkedin"},
    )
    assert created.status_code == 201
    prospect_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/prospects/{prospect_id}",
        headers=headers,
        json={"company": "Notox", "city": "Anglet", "status": "envoye", "channel": "linkedin", "sentOn": "2026-11-03"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "envoye"
    removed = client.delete(f"/api/v1/prospects/{prospect_id}", headers=headers)
    assert removed.status_code == 204
    names = [item["company"] for item in client.get("/api/v1/prospects", headers=headers).json()["items"]]
    assert names == ["Purenat"]
