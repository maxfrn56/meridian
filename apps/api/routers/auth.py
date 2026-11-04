from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import AuthOut, LoginIn, RegisterIn, UserOut
from routers.deps import current_user
from security import hash_password, issue_token, verify_password
from store import User, Workspace, store

router = APIRouter(prefix="/auth", tags=["auth"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _user_out(user: User) -> UserOut:
    workspace = store.workspace_for(user.id)
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        workspace_name=workspace.name if workspace else "",
        brand_name=workspace.brand_name if workspace else "",
        domain=workspace.domain if workspace else "",
    )


@router.post("/register", response_model=AuthOut)
def register(payload: RegisterIn) -> AuthOut:
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Adresse e-mail invalide.")
    if store.user_by_email(email):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet e-mail.")
    user = User(
        id=uuid.uuid4().hex,
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    store.add_user(
        user,
        Workspace(
            id=uuid.uuid4().hex,
            user_id=user.id,
            name=payload.name.strip(),
            brand_name=payload.name.strip(),
            domain="",
            sector="",
        ),
    )
    return AuthOut(token=issue_token(user.id), user=_user_out(user))


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn) -> AuthOut:
    user = store.user_by_email(payload.email.strip().lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    return AuthOut(token=issue_token(user.id), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return _user_out(user)
