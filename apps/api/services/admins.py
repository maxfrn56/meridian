"""Comptes internes de Valentin et Maxime.

ADMIN_ACCOUNTS=Nom|email|motdepasse;Autre|email|motdepasse

Au redémarrage, le mot de passe de la variable devient celui du compte.
Un compte déjà inscrit est confirmé et passe administrateur.
"""

from __future__ import annotations

import logging
import os
import uuid

from security import hash_password, password_is_strong, verify_password
from store import User, store

logger = logging.getLogger(__name__)


def listed_accounts() -> list[tuple[str, str, str]]:
    raw = os.getenv("ADMIN_ACCOUNTS", "")
    accounts: list[tuple[str, str, str]] = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [part.strip() for part in chunk.split("|")]
        if len(parts) >= 3 and "@" in parts[1]:
            accounts.append((parts[0], parts[1].lower(), "|".join(parts[2:])))
            continue
        if len(parts) == 2 and "@" in parts[0]:
            name = parts[0].split("@", 1)[0] or "Admin"
            accounts.append((name, parts[0].lower(), parts[1]))
            continue
        logger.error("ADMIN_ACCOUNTS : entrée ignorée, format Nom|email|motdepasse attendu.")
    return accounts


def is_listed_admin(email: str) -> bool:
    return email.lower() in {item[1] for item in listed_accounts()}


def grant_listed_admin(user: User) -> User:
    if user.role != "admin" and is_listed_admin(user.email):
        store.set_role(user.id, "admin")
        user.role = "admin"
    return user


def ensure_admins() -> None:
    for name, email, password in listed_accounts():
        existing = store.user_by_email(email)
        if existing is not None:
            replacement = None
            if password_is_strong(password) and not verify_password(password, existing.password_hash):
                replacement = hash_password(password)
            if existing.role != "admin" or not existing.email_verified or replacement:
                store.adopt_admin(existing.id, replacement)
            continue
        if len(name) < 2 or not password_is_strong(password):
            logger.error("Compte administrateur %s ignoré : nom ou mot de passe invalide.", email)
            continue
        store.add_admin(
            User(
                id=uuid.uuid4().hex,
                name=name,
                email=email,
                password_hash=hash_password(password),
                email_verified=True,
                role="admin",
            )
        )
        logger.info("Compte administrateur créé pour %s", email)
