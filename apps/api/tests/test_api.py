import hashlib
import hmac
import json
import os
import re
import time

import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app
from seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo
from services.mail import OUTBOX
from store import store


@pytest.fixture()
def client():
    previous = settings.mock_llm
    previous_resend = os.environ.pop("RESEND_API_KEY", None)
    previous_admins = os.environ.pop("ADMIN_ACCOUNTS", None)
    stripe_names = (
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRICE_ESSENTIEL",
        "STRIPE_PRICE_CROISSANCE",
        "STRIPE_PRICE_REFERENCE",
    )
    previous_stripe = {name: os.environ.pop(name, None) for name in stripe_names}
    os.environ["MAIL_CAPTURE"] = "true"
    object.__setattr__(settings, "mock_llm", "true")
    store.reset()
    OUTBOX.clear()
    seed_demo(store)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        object.__setattr__(settings, "mock_llm", previous)
        os.environ.pop("MAIL_CAPTURE", None)
        if previous_resend is not None:
            os.environ["RESEND_API_KEY"] = previous_resend
        if previous_admins is not None:
            os.environ["ADMIN_ACCOUNTS"] = previous_admins
        for name, value in previous_stripe.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        OUTBOX.clear()


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
    # Les concurrents ne sont pas déclarés : ce sont les marques les plus nommées dans les réponses.
    discovered = audit.json()["discoveredCompetitors"]
    names = [item["name"] for item in discovered]
    assert names[0] == "Lumenboard"
    assert "Northwind" not in names
    assert [item["mentions"] for item in discovered] == sorted((item["mentions"] for item in discovered), reverse=True)
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
    rivals = [item["name"] for item in body["entities"][1:]]
    assert len(rivals) == 5
    assert all(item["kind"] == "competitor" for item in body["entities"][1:])
    assert {"Lumenboard", "Stackmetric"} <= set(rivals)
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


def _stripe_signature(body: bytes, secret: str) -> str:
    stamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={digest}"


def test_stripe_checkout_opens_test_session_and_webhook_activates_plan(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
    os.environ["STRIPE_PRICE_ESSENTIEL"] = "price_essentiel"
    captured: dict[str, object] = {}

    class Response:
        status_code = 200

        def json(self):
            return {"url": "https://checkout.stripe.com/c/pay/cs_test_abc"}

    def fake_post(url, headers=None, data=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        return Response()

    monkeypatch.setattr("services.payments.httpx.post", fake_post)
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    blocked = client.post("/api/v1/billing", headers=headers, json={"planId": "essentiel"})
    assert blocked.status_code == 409
    opened = client.post("/api/v1/billing/checkout", headers=headers, json={"planId": "essentiel"})
    assert opened.status_code == 200
    assert opened.json()["url"] == "https://checkout.stripe.com/c/pay/cs_test_abc"
    assert captured["headers"]["Authorization"] == "Bearer sk_test_fake"
    assert captured["data"]["line_items[0][price]"] == "price_essentiel"
    assert captured["data"]["mode"] == "subscription"

    user = store.user_by_email(DEMO_EMAIL)
    workspace = store.workspace_for(user.id)
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "mode": "subscription",
                "status": "complete",
                "payment_status": "paid",
                "customer": "cus_test",
                "subscription": "sub_test",
                "metadata": {"workspace_id": workspace.id, "plan_id": "essentiel"},
            }
        },
    }
    body = json.dumps(event).encode()
    refused = client.post(
        "/api/v1/billing/webhook",
        content=body,
        headers={"Stripe-Signature": "t=1,v1=dead", "Content-Type": "application/json"},
    )
    assert refused.status_code == 400
    accepted = client.post(
        "/api/v1/billing/webhook",
        content=body,
        headers={"Stripe-Signature": _stripe_signature(body, "whsec_test"), "Content-Type": "application/json"},
    )
    assert accepted.status_code == 200
    billing = client.get("/api/v1/billing", headers=headers).json()
    assert billing["plan"]["id"] == "essentiel"

    ended = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"metadata": {"workspace_id": workspace.id}}},
    }
    ended_body = json.dumps(ended).encode()
    cleared = client.post(
        "/api/v1/billing/webhook",
        content=ended_body,
        headers={"Stripe-Signature": _stripe_signature(ended_body, "whsec_test"), "Content-Type": "application/json"},
    )
    assert cleared.status_code == 200
    assert client.get("/api/v1/billing", headers=headers).json()["plan"] is None


def test_settings_no_longer_carry_competitors(client: TestClient):
    headers = {"Authorization": f"Bearer {_token(client)}"}
    current = client.get("/api/v1/settings", headers=headers).json()
    assert "competitors" not in current
    response = client.put("/api/v1/settings", headers=headers, json={**current, "competitors": [{"name": "X", "domain": "x.io"}]})
    assert response.status_code == 200
    assert "competitors" not in response.json()


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


def _admin_headers(client: TestClient, name: str, email: str) -> dict[str, str]:
    import uuid

    from security import hash_password
    from store import User

    if store.user_by_email(email) is None:
        store.add_admin(
            User(
                id=uuid.uuid4().hex,
                name=name,
                email=email,
                password_hash=hash_password("adminpass8"),
                email_verified=True,
                role="admin",
            )
        )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "adminpass8"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_prospects_crud_in_database(client: TestClient):
    headers = _admin_headers(client, "Maxime", "maxime@geo.dev")
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


def _link_token() -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", OUTBOX[-1]["body"])
    assert match
    return match.group(1)


def _confirmed_token(client: TestClient, email: str, password: str) -> str:
    assert client.post("/api/v1/auth/verify", json={"token": _link_token()}).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["token"]


def test_prospects_are_shared_by_admins_and_hidden_from_clients(client: TestClient):
    maxime = _admin_headers(client, "Maxime", "maxime@geo.dev")
    valentin = _admin_headers(client, "Valentin", "valentin@geo.dev")
    demo = {"Authorization": f"Bearer {_token(client)}"}
    assert client.get("/api/v1/prospects", headers=demo).status_code == 403
    listing = client.get("/api/v1/prospects", headers=maxime)
    assert listing.status_code == 200
    prospect_id = listing.json()["items"][0]["id"]
    shared = client.get("/api/v1/prospects", headers=valentin).json()["items"]
    assert shared[0]["id"] == prospect_id
    assert client.delete(f"/api/v1/prospects/{prospect_id}", headers=demo).status_code == 403
    created = client.post(
        "/api/v1/prospects",
        headers=maxime,
        json={"company": "Notox", "city": "Anglet", "status": "a_contacter", "channel": "linkedin"},
    )
    assert created.status_code == 201
    names = {item["company"] for item in client.get("/api/v1/prospects", headers=valentin).json()["items"]}
    assert names == {"Purenat", "Notox"}


def test_data_survives_an_api_restart(client: TestClient):
    created = client.post(
        "/api/v1/auth/register", json={"name": "Acme", "email": "acme@example.com", "password": "motdepasse8"}
    )
    assert created.status_code == 200
    headers = {"Authorization": f"Bearer {_confirmed_token(client, 'acme@example.com', 'motdepasse8')}"}
    payload = client.get("/api/v1/settings", headers=headers).json()
    payload.update(domain="acme.fr", sector="Logiciel", queries=[{"prompt": "Meilleur outil GEO ?", "active": True}])
    assert client.put("/api/v1/settings", headers=headers, json=payload).status_code == 200
    # Un nouveau cycle de vie = un redémarrage : rien n'est gardé en mémoire entre les deux.
    with TestClient(app) as restarted:
        login = restarted.post("/api/v1/auth/login", json={"email": "acme@example.com", "password": "motdepasse8"})
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
    payload["queries"] = before["queries"][:3]
    after = client.put("/api/v1/settings", headers=headers, json=payload).json()
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
    headers = _admin_headers(client, "Maxime", "maxime@geo.dev")
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
    headers = _admin_headers(client, "Maxime", "maxime@geo.dev")
    names = {item["company"] for item in client.get("/api/v1/prospects", headers=headers).json()["items"]}
    assert "Équipe Windows" in names


def test_unreadable_legacy_file_does_not_block_startup(tmp_path):
    from services.prospects import import_legacy_file

    legacy = tmp_path / "prospects.json"
    legacy.write_text("{ pas du json", encoding="utf-8")
    assert import_legacy_file(legacy) == 0
    assert legacy.exists()


def test_admin_overview_counts_client_subscriptions(client: TestClient):
    headers = _admin_headers(client, "Maxime", "maxime@geo.dev")
    denied = client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {_token(client)}"})
    assert denied.status_code == 403
    body = client.get("/api/v1/admin/overview", headers=headers).json()
    assert body["accounts"] == 1
    assert body["verifiedAccounts"] == 1
    assert body["subscriptions"] == 1
    assert body["monthlyRevenueEur"] == 189.9
    assert body["clients"][0]["email"] == DEMO_EMAIL
    assert body["clients"][0]["planName"] == "Croissance"
    assert body["clients"][0]["priceEur"] == 189.9
    croissance = next(item for item in body["plans"] if item["id"] == "croissance")
    assert croissance["subscribers"] == 1
    assert croissance["monthlyEur"] == 189.9
    assert all(item["email"] != "maxime@geo.dev" for item in body["clients"])


def test_environment_creates_admin_accounts(client: TestClient):
    from services.admins import ensure_admins

    os.environ["ADMIN_ACCOUNTS"] = "Maxime|maxime.admin@geo.dev|meridian8;Valentin|valentin.admin@geo.dev|meridian8"
    try:
        ensure_admins()
        ensure_admins()
        login = client.post(
            "/api/v1/auth/login", json={"email": "valentin.admin@geo.dev", "password": "meridian8"}
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "admin"
        assert store.user_by_email("maxime.admin@geo.dev").role == "admin"
        os.environ["ADMIN_ACCOUNTS"] = "Camille Martin|demo@geo.dev|autrepass1"
        ensure_admins()
        old = client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        assert old.status_code == 401
        still = client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": "autrepass1"})
        assert still.status_code == 200
        assert still.json()["user"]["role"] == "admin"
        os.environ["ADMIN_ACCOUNTS"] = "contact@geo.dev|meridian8"
        ensure_admins()
        short = client.post("/api/v1/auth/login", json={"email": "contact@geo.dev", "password": "meridian8"})
        assert short.status_code == 200
        assert short.json()["user"]["role"] == "admin"
        os.environ["ADMIN_ACCOUNTS"] = "Trop court|court@geo.dev|abc"
        ensure_admins()
        assert store.user_by_email("court@geo.dev") is None
    finally:
        os.environ.pop("ADMIN_ACCOUNTS", None)


def test_signup_requires_email_confirmation_and_password_reset(client: TestClient):
    email = "ada@example.com"
    created = client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Martin", "email": email, "password": "meridian8"},
    )
    assert created.status_code == 200
    assert "boîte mail" in created.json()["message"]
    blocked = client.post("/api/v1/auth/login", json={"email": email, "password": "meridian8"})
    assert blocked.status_code == 403
    confirmed = client.post("/api/v1/auth/verify", json={"token": _link_token()})
    assert confirmed.status_code == 200
    reused = client.post("/api/v1/auth/verify", json={"token": _link_token()})
    assert reused.status_code == 400
    session = client.post("/api/v1/auth/login", json={"email": email, "password": "meridian8"})
    assert session.status_code == 200
    old_token = session.json()["token"]

    unknown = client.post("/api/v1/auth/forgot", json={"email": "absent@example.com"})
    assert unknown.status_code == 200
    assert unknown.json()["message"] == client.post("/api/v1/auth/forgot", json={"email": email}).json()["message"]
    weak = client.post("/api/v1/auth/reset", json={"token": _link_token(), "password": "meridian"})
    assert weak.status_code == 422
    reset = client.post("/api/v1/auth/reset", json={"token": _link_token(), "password": "meridian9"})
    assert reset.status_code == 200
    stale = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert stale.status_code == 401
    again = client.post("/api/v1/auth/login", json={"email": email, "password": "meridian9"})
    assert again.status_code == 200
