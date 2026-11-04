from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import AuthOut, EmailIn, LoginIn, MessageOut, RegisterIn, ResetIn, TokenIn, UserOut
from routers.deps import current_user
from security import hash_password, issue_token, password_is_strong, verify_password
from services.admins import grant_listed_admin
from services.mail import MailError, app_base_url, mail_configured, send_email
from store import User, Workspace, store

router = APIRouter(prefix="/auth", tags=["auth"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WEAK_PASSWORD = "Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre."
LINK_INVALID = "Ce lien n'est plus valable. Demandez-en un nouveau."
MAIL_SENT = "Si un compte correspond à cette adresse, un e-mail vient d'être envoyé."


def _user_out(user: User) -> UserOut:
    workspace = store.workspace_for(user.id)
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role="admin" if user.role == "admin" else "client",
        workspace_name=workspace.name if workspace else "",
        brand_name=workspace.brand_name if workspace else "",
        domain=workspace.domain if workspace else "",
    )


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _mail_ready() -> None:
    if not mail_configured():
        raise HTTPException(status_code=503, detail="L'envoi des e-mails n'est pas configuré.")


def _deliver(recipient: str, subject: str, body: str) -> None:
    try:
        send_email(recipient, subject, body)
    except MailError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def _send_verification(user: User, *, force: bool) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    if not store.stage_token(user.id, "verify", _digest(token), expires, force=force):
        return
    link = f"{app_base_url()}/verify-email?token={token}"
    _deliver(
        user.email,
        "Confirmez votre inscription Meridian",
        (
            f"Bonjour {user.name},\n\n"
            "Confirmez votre adresse pour activer votre espace Meridian :\n"
            f"{link}\n\n"
            "Ce lien expire dans 24 heures. Si vous n'êtes pas à l'origine de cette inscription, ignorez ce message.\n"
        ),
    )
    store.mark_mail_sent(user.id, "verify")


def _send_reset(user: User) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    if not store.stage_token(user.id, "reset", _digest(token), expires, force=False):
        return
    link = f"{app_base_url()}/reset-password?token={token}"
    _deliver(
        user.email,
        "Réinitialiser votre mot de passe Meridian",
        (
            f"Bonjour {user.name},\n\n"
            "Choisissez un nouveau mot de passe pour votre espace Meridian :\n"
            f"{link}\n\n"
            "Ce lien expire dans 1 heure et ne fonctionne qu'une fois. "
            "Si vous n'avez pas demandé cette réinitialisation, ignorez ce message.\n"
        ),
    )
    store.mark_mail_sent(user.id, "reset")


@router.post("/register", response_model=MessageOut)
def register(payload: RegisterIn) -> MessageOut:
    _mail_ready()
    email = payload.email.strip().lower()
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Indiquez votre nom.")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Adresse e-mail invalide.")
    if not password_is_strong(payload.password):
        raise HTTPException(status_code=422, detail=WEAK_PASSWORD)
    if store.user_by_email(email):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet e-mail.")
    user = User(
        id=uuid.uuid4().hex,
        name=name,
        email=email,
        password_hash=hash_password(payload.password),
        email_verified=False,
    )
    try:
        store.add_user(
            user,
            Workspace(
                id=uuid.uuid4().hex,
                user_id=user.id,
                name=name,
                brand_name=name,
                domain="",
                sector="",
            ),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    try:
        _send_verification(user, force=True)
    except HTTPException:
        _discard_new_account(user.id)
        raise
    except Exception as error:
        _discard_new_account(user.id)
        raise HTTPException(status_code=503, detail="L'e-mail de confirmation n'a pas pu être envoyé.") from error
    return MessageOut(message="Consultez votre boîte mail pour confirmer l'inscription. Le lien expire dans 24 heures.")


def _discard_new_account(user_id: str) -> None:
    try:
        store.delete_user(user_id)
    except Exception:
        return


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn) -> AuthOut:
    user = store.user_by_email(payload.email.strip().lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    user = grant_listed_admin(user)
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Confirmez votre adresse e-mail avant de vous connecter.")
    return AuthOut(token=issue_token(user.id, user.session_version), user=_user_out(user))


@router.post("/resend", response_model=MessageOut)
def resend(payload: EmailIn) -> MessageOut:
    _mail_ready()
    email = payload.email.strip().lower()
    user = store.user_by_email(email) if EMAIL_RE.match(email) else None
    if user is not None and not user.email_verified:
        _send_verification(user, force=False)
    return MessageOut(message=MAIL_SENT)


@router.post("/verify", response_model=MessageOut)
def verify(payload: TokenIn) -> MessageOut:
    if not store.confirm_email(_digest(payload.token.strip())):
        raise HTTPException(status_code=400, detail=LINK_INVALID)
    return MessageOut(message="Adresse confirmée. Vous pouvez vous connecter.")


@router.post("/forgot", response_model=MessageOut)
def forgot(payload: EmailIn) -> MessageOut:
    _mail_ready()
    email = payload.email.strip().lower()
    user = store.user_by_email(email) if EMAIL_RE.match(email) else None
    if user is not None:
        _send_reset(user)
    return MessageOut(message=MAIL_SENT)


@router.post("/reset", response_model=MessageOut)
def reset_password(payload: ResetIn) -> MessageOut:
    if not password_is_strong(payload.password):
        raise HTTPException(status_code=422, detail=WEAK_PASSWORD)
    if not store.reset_password(_digest(payload.token.strip()), hash_password(payload.password)):
        raise HTTPException(status_code=400, detail=LINK_INVALID)
    return MessageOut(message="Mot de passe mis à jour. Connectez-vous avec le nouveau.")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return _user_out(user)
