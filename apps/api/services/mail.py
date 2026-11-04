from __future__ import annotations

import os

import httpx

OUTBOX: list[dict[str, str]] = []
RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "Meridian <onboarding@resend.dev>"


class MailError(RuntimeError):
    pass


def app_base_url() -> str:
    explicit = os.getenv("APP_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if domain:
        return f"https://{domain}"
    return "http://localhost:3000"


def _capture() -> bool:
    return os.getenv("MAIL_CAPTURE", "").strip().lower() in {"1", "true", "yes"}


def mail_configured() -> bool:
    return _capture() or bool(os.getenv("RESEND_API_KEY", "").strip())


def send_email(recipient: str, subject: str, body: str) -> None:
    if _capture():
        OUTBOX.append({"to": recipient, "subject": subject, "body": body})
        return
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        raise MailError("L'envoi des e-mails n'est pas configuré.")
    sender = os.getenv("RESEND_FROM", "").strip() or DEFAULT_FROM
    try:
        response = httpx.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"from": sender, "to": [recipient], "subject": subject, "text": body},
            timeout=20,
        )
    except httpx.HTTPError as error:
        raise MailError("L'e-mail n'a pas pu être envoyé.") from error
    if response.status_code >= 400:
        detail = "Resend a refusé l'envoi. Vérifiez la clé API et l'adresse d'expéditeur."
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("message"), str):
            detail = f"Resend a refusé l'envoi : {payload['message']}"[:300]
        raise MailError(detail)
