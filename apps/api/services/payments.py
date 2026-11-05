"""Paiement Stripe. Une clé sk_test_ ouvre l'environnement de test, une clé sk_live_ les vrais paiements."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time

import httpx

from services.billing import plan_by_id
from services.mail import app_base_url
from store import Workspace, store

CHECKOUT_URL = "https://api.stripe.com/v1/checkout/sessions"
SUBSCRIPTIONS_URL = "https://api.stripe.com/v1/subscriptions"
PRICE_ENV = {
    "essentiel": "STRIPE_PRICE_ESSENTIEL",
    "croissance": "STRIPE_PRICE_CROISSANCE",
    "reference": "STRIPE_PRICE_REFERENCE",
}


class PaymentError(RuntimeError):
    pass


def _secret() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def _webhook_secret() -> str:
    return os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()


def enabled() -> bool:
    return bool(_secret())


def _price_for(plan_id: str) -> str:
    return os.getenv(PRICE_ENV.get(plan_id, ""), "").strip()


def _plan_for_price(price_id: str) -> str | None:
    if not price_id:
        return None
    for plan_id in PRICE_ENV:
        if _price_for(plan_id) == price_id:
            return plan_id
    return None


def start_checkout(workspace: Workspace, email: str, plan_id: str) -> str:
    if plan_by_id(plan_id) is None:
        raise ValueError("Forfait inconnu.")
    if not enabled():
        raise PaymentError("Le paiement Stripe n'est pas configuré.")
    price = _price_for(plan_id)
    if not price:
        raise PaymentError("Le prix Stripe de ce forfait n'est pas configuré.")
    base = app_base_url()
    form = {
        "mode": "subscription",
        "client_reference_id": workspace.id,
        "success_url": f"{base}/billing?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/billing?checkout=cancel",
        "locale": "fr",
        "line_items[0][price]": price,
        "line_items[0][quantity]": "1",
        "metadata[workspace_id]": workspace.id,
        "metadata[plan_id]": plan_id,
        "subscription_data[metadata][workspace_id]": workspace.id,
        "subscription_data[metadata][plan_id]": plan_id,
    }
    customer = store.stripe_customer_id(workspace.id)
    if customer:
        form["customer"] = customer
    else:
        form["customer_email"] = email
    try:
        response = httpx.post(
            CHECKOUT_URL,
            headers={"Authorization": f"Bearer {_secret()}"},
            data=form,
            timeout=20,
        )
    except httpx.HTTPError as error:
        raise PaymentError("Stripe est injoignable.") from error
    if response.status_code >= 400:
        detail = "Stripe a refusé l'ouverture du paiement."
        try:
            payload = response.json()
        except ValueError:
            payload = None
        message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        if isinstance(message, str) and message:
            detail = f"Stripe a refusé l'ouverture du paiement : {message}"[:300]
        raise PaymentError(detail)
    url = response.json().get("url")
    if not isinstance(url, str) or not url:
        raise PaymentError("Stripe n'a pas renvoyé de page de paiement.")
    return url


def event_from(payload: bytes, signature: str) -> dict:
    secret = _webhook_secret()
    if not secret:
        raise PaymentError("Le secret du webhook Stripe n'est pas configuré.")
    parts: dict[str, list[str]] = {}
    for item in signature.split(","):
        key, _, value = item.partition("=")
        if key and value:
            parts.setdefault(key, []).append(value)
    timestamps = parts.get("t") or []
    signatures = parts.get("v1") or []
    if not timestamps or not signatures:
        raise PaymentError("Signature Stripe invalide.")
    try:
        stamp = int(timestamps[0])
    except ValueError as error:
        raise PaymentError("Signature Stripe invalide.") from error
    if abs(int(time.time()) - stamp) > 300:
        raise PaymentError("Signature Stripe expirée.")
    signed = f"{stamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, item) for item in signatures):
        raise PaymentError("Signature Stripe invalide.")
    try:
        event = json.loads(payload)
    except ValueError as error:
        raise PaymentError("Événement Stripe illisible.") from error
    if not isinstance(event, dict):
        raise PaymentError("Événement Stripe illisible.")
    return event


def _cancel_subscription(subscription_id: str) -> None:
    if not subscription_id or not enabled():
        return
    try:
        httpx.delete(
            f"{SUBSCRIPTIONS_URL}/{subscription_id}",
            headers={"Authorization": f"Bearer {_secret()}"},
            timeout=20,
        )
    except httpx.HTTPError:
        return


def _price_on_subscription(data: dict) -> str:
    items = data.get("items") if isinstance(data.get("items"), dict) else {}
    rows = items.get("data") if isinstance(items, dict) else None
    if not isinstance(rows, list) or not rows:
        return ""
    price = rows[0].get("price") if isinstance(rows[0], dict) else None
    if isinstance(price, dict) and isinstance(price.get("id"), str):
        return price["id"]
    return ""


def _stripe_get(url: str) -> dict:
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {_secret()}"}, timeout=20)
    except httpx.HTTPError as error:
        raise PaymentError("Stripe est injoignable.") from error
    if response.status_code >= 400:
        raise PaymentError("Stripe n'a pas pu confirmer le paiement.")
    payload = response.json()
    if not isinstance(payload, dict):
        raise PaymentError("Stripe n'a pas pu confirmer le paiement.")
    return payload


def _owned(workspace_id: str, session: dict) -> bool:
    if session.get("client_reference_id") == workspace_id:
        return True
    meta = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    return meta.get("workspace_id") == workspace_id


def _paid_subscription(session: dict) -> bool:
    return (
        session.get("mode") == "subscription"
        and session.get("status") == "complete"
        and session.get("payment_status") in {"paid", "no_payment_required"}
    )


def _grant_session(session: dict) -> None:
    meta = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    workspace_id = meta.get("workspace_id") if isinstance(meta.get("workspace_id"), str) else ""
    if not workspace_id and isinstance(session.get("client_reference_id"), str):
        workspace_id = session["client_reference_id"]
    plan_id = meta.get("plan_id") if isinstance(meta.get("plan_id"), str) else ""
    if not workspace_id or plan_by_id(plan_id) is None:
        raise PaymentError("Ce paiement ne correspond pas à un forfait.")
    customer = session.get("customer") if isinstance(session.get("customer"), str) else ""
    subscription = session.get("subscription") if isinstance(session.get("subscription"), str) else ""
    previous = store.apply_paid_plan(workspace_id, plan_id, customer, subscription)
    if previous:
        _cancel_subscription(previous)


def confirm_checkout(workspace: Workspace, session_id: str | None) -> bool:
    """Active le forfait à partir de la session Stripe, sans attendre le webhook."""
    if not enabled():
        raise PaymentError("Le paiement Stripe n'est pas configuré.")
    if session_id:
        if re.fullmatch(r"cs_[A-Za-z0-9_]+", session_id) is None:
            raise PaymentError("Paiement introuvable.")
        session = _stripe_get(f"{CHECKOUT_URL}/{session_id}")
        if not _owned(workspace.id, session):
            raise PaymentError("Ce paiement ne correspond pas à cet espace.")
        if not _paid_subscription(session):
            raise PaymentError("Le paiement n'est pas terminé.")
        _grant_session(session)
        return True
    payload = _stripe_get(f"{CHECKOUT_URL}?limit=20")
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    for session in rows:
        if isinstance(session, dict) and _owned(workspace.id, session) and _paid_subscription(session):
            _grant_session(session)
            return True
    return False


def apply_event(event: dict) -> None:
    kind = event.get("type")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    obj = data.get("object") if isinstance(data.get("object"), dict) else {}
    meta = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    workspace_id = meta.get("workspace_id") if isinstance(meta.get("workspace_id"), str) else ""
    if kind == "checkout.session.completed":
        if obj.get("mode") != "subscription" or obj.get("status") != "complete":
            return
        if obj.get("payment_status") not in {"paid", "no_payment_required"}:
            return
        plan_id = meta.get("plan_id") if isinstance(meta.get("plan_id"), str) else ""
        if not workspace_id or plan_by_id(plan_id) is None:
            return
        customer = obj.get("customer") if isinstance(obj.get("customer"), str) else ""
        subscription = obj.get("subscription") if isinstance(obj.get("subscription"), str) else ""
        previous = store.apply_paid_plan(workspace_id, plan_id, customer, subscription)
        if previous:
            _cancel_subscription(previous)
        return
    if kind == "customer.subscription.updated":
        if not workspace_id:
            return
        status = obj.get("status")
        if status in {"active", "trialing"}:
            plan_id = _plan_for_price(_price_on_subscription(obj))
            if plan_id is None and isinstance(meta.get("plan_id"), str):
                plan_id = meta["plan_id"]
            if plan_by_id(plan_id) is None:
                return
            customer = obj.get("customer") if isinstance(obj.get("customer"), str) else ""
            subscription = obj.get("id") if isinstance(obj.get("id"), str) else ""
            previous = store.apply_paid_plan(workspace_id, plan_id, customer, subscription)
            if previous:
                _cancel_subscription(previous)
            return
        if status in {"canceled", "unpaid", "incomplete_expired"}:
            store.clear_paid_plan(workspace_id)
        return
    if kind == "customer.subscription.deleted" and workspace_id:
        store.clear_paid_plan(workspace_id)
