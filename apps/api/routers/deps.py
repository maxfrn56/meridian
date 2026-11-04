from __future__ import annotations

from fastapi import Header, HTTPException

from security import read_token
from store import User, Workspace, store


def current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise.")
    parsed = read_token(authorization.split(" ", 1)[1].strip())
    user = store.user_by_id(parsed[0]) if parsed else None
    if user is None or parsed is None or user.session_version != parsed[1]:
        raise HTTPException(status_code=401, detail="Session expirée.")
    return user


def current_workspace(authorization: str | None = Header(default=None)) -> Workspace:
    user = current_user(authorization)
    workspace = store.workspace_for(user.id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Espace introuvable.")
    return workspace
