import json

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


def test_prospects_crud_in_database(client: TestClient):
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


def test_prospects_are_private_to_their_owner(client: TestClient):
    demo = {"Authorization": f"Bearer {_token(client)}"}
    prospect_id = client.get("/api/v1/prospects", headers=demo).json()["items"][0]["id"]
    other = client.post(
        "/api/v1/auth/register", json={"name": "Autre", "email": "autre@example.com", "password": "motdepasse"}
    ).json()["token"]
    intruder = {"Authorization": f"Bearer {other}"}
    assert client.get("/api/v1/prospects", headers=intruder).json()["items"] == []
    assert client.delete(f"/api/v1/prospects/{prospect_id}", headers=intruder).status_code == 404


def test_data_survives_an_api_restart(client: TestClient):
    created = client.post(
        "/api/v1/auth/register", json={"name": "Acme", "email": "acme@example.com", "password": "motdepasse"}
    )
    assert created.status_code == 200
    headers = {"Authorization": f"Bearer {created.json()['token']}"}
    payload = client.get("/api/v1/settings", headers=headers).json()
    payload.update(domain="acme.fr", sector="Logiciel", queries=[{"prompt": "Meilleur outil GEO ?", "active": True}])
    assert client.put("/api/v1/settings", headers=headers, json=payload).status_code == 200
    # Un nouveau cycle de vie = un redémarrage : rien n'est gardé en mémoire entre les deux.
    with TestClient(app) as restarted:
        login = restarted.post("/api/v1/auth/login", json={"email": "acme@example.com", "password": "motdepasse"})
        assert login.status_code == 200
        settings_after = restarted.get(
            "/api/v1/settings", headers={"Authorization": f"Bearer {login.json()['token']}"}
        ).json()
    assert settings_after["domain"] == "acme.fr"
    assert [item["prompt"] for item in settings_after["queries"]] == ["Meilleur outil GEO ?"]


def test_editing_settings_keeps_ids_of_unchanged_items(client: TestClient):
    headers = {"Authorization": f"Bearer {_token(client)}"}
    before = client.get("/api/v1/settings", headers=headers).json()
    payload = dict(before)
    payload["competitors"] = before["competitors"][1:] + [{"name": "Nouveau", "domain": "nouveau.example"}]
    payload["queries"] = before["queries"][:3]
    after = client.put("/api/v1/settings", headers=headers, json=payload).json()
    assert [item["id"] for item in after["competitors"][:-1]] == [item["id"] for item in before["competitors"][1:]]
    assert [item["id"] for item in after["queries"]] == [item["id"] for item in before["queries"][:3]]
    # Les réponses déjà collectées pour les prompts retirés restent en base.
    tracking = client.get("/api/v1/tracking", headers=headers).json()
    assert len(tracking["queries"]) == 3


def test_legacy_prospects_file_is_imported_once(client: TestClient, tmp_path):
    from seed import DEMO_EMAIL as email
    from services.prospects import import_legacy_file
    from store import store as data

    user_id = data.user_by_email(email).id
    legacy = tmp_path / "prospects.json"
    legacy.write_text(
        json.dumps(
            {
                user_id: [
                    {
                        "id": "abc123",
                        "company": "Ancien",
                        "channel": "email",
                        "status": "rdv",
                        "createdAt": "2026-10-01T09:00:00+00:00",
                        "updatedAt": "2026-10-02T09:00:00+00:00",
                    }
                ],
                "compte-disparu": [{"id": "zzz", "company": "Perdu", "channel": "email", "status": "envoye"}],
            }
        ),
        encoding="utf-8",
    )
    assert import_legacy_file(legacy) == 1
    assert not legacy.exists()
    headers = {"Authorization": f"Bearer {_token(client)}"}
    names = {item["company"] for item in client.get("/api/v1/prospects", headers=headers).json()["items"]}
    assert names == {"Purenat", "Ancien"}


def test_legacy_file_written_by_windows_is_readable(client: TestClient, tmp_path):
    from seed import DEMO_EMAIL as email
    from services.prospects import import_legacy_file
    from store import store as data

    user_id = data.user_by_email(email).id
    legacy = tmp_path / "prospects.json"
    content = json.dumps({user_id: [{"id": "win1", "company": "Équipe Windows", "channel": "email", "status": "envoye"}]}, ensure_ascii=False)
    legacy.write_bytes(content.encode("cp1252"))
    assert import_legacy_file(legacy) == 1
    headers = {"Authorization": f"Bearer {_token(client)}"}
    names = {item["company"] for item in client.get("/api/v1/prospects", headers=headers).json()["items"]}
    assert "Équipe Windows" in names


def test_unreadable_legacy_file_does_not_block_startup(tmp_path):
    from services.prospects import import_legacy_file

    legacy = tmp_path / "prospects.json"
    legacy.write_text("{ pas du json", encoding="utf-8")
    assert import_legacy_file(legacy) == 0
    assert legacy.exists()
