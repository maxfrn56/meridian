from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from db import session_scope
from models.schemas import ProspectIn, ProspectListOut, ProspectOut, ProspectSummary
from models.tables import ProspectRow, UserRow

# Ancien stockage (avant la base). Importé une fois au démarrage s'il existe.
LEGACY_PATH = Path(__file__).resolve().parents[1] / "data" / "prospects.json"
FIELDS = tuple(ProspectIn.model_fields)
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _out(row: ProspectRow) -> ProspectOut:
    values = {name: getattr(row, name) for name in FIELDS}
    return ProspectOut(id=row.id, created_at=_aware(row.created_at), updated_at=_aware(row.updated_at), **values)


def _apply(row: ProspectRow, payload: ProspectIn) -> None:
    for name, value in payload.model_dump().items():
        setattr(row, name, value)


def demo_prospects() -> list[ProspectIn]:
    today = date.today()
    return [
        ProspectIn(
            company="Purenat",
            contact_name="Équipe Purenat",
            email="contact@pure-nat.com",
            website="https://www.pure-nat.com",
            city="Bayonne",
            question=(
                "Comment faire baisser les COV dans une crèche ?\n"
                "Quel filtre détruit le formaldéhyde ?\n"
                "Quoi intégrer dans une centrale de traitement d’air ?"
            ),
            channel="email",
            status="envoye",
            sent_on=today.isoformat(),
            follow_up_on=(today + timedelta(days=4)).isoformat(),
            meeting_on=None,
            amount_eur=1500,
            next_step="Relancer si aucune réponse.",
            notes=(
                "Mail envoyé à contact@pure-nat.com. "
                "Trois questions d’acheteurs, sans statistique ni présentation d’outil."
            ),
        )
    ]


def seed_prospects(user_id: str) -> None:
    with session_scope() as session:
        for payload in demo_prospects():
            # Même identifiant que l'ancien fichier JSON : l'import le reconnaît au lieu de le dupliquer.
            row = ProspectRow(id=uuid.uuid5(uuid.NAMESPACE_URL, payload.company.lower()).hex, user_id=user_id)
            _apply(row, payload)
            session.add(row)


def _summary(items: list[ProspectOut]) -> ProspectSummary:
    today = date.today().isoformat()
    waiting = {"envoye", "relance"}
    return ProspectSummary(
        total=len(items),
        to_contact=sum(1 for item in items if item.status == "a_contacter"),
        waiting=sum(1 for item in items if item.status in waiting),
        follow_ups_due=sum(
            1 for item in items if item.status in waiting and item.follow_up_on and item.follow_up_on <= today
        ),
        meetings=sum(1 for item in items if item.status == "rdv"),
    )


def list_prospects(user_id: str) -> ProspectListOut:
    with session_scope() as session:
        rows = session.scalars(select(ProspectRow).where(ProspectRow.user_id == user_id)).all()
        items = [_out(row) for row in rows]
    items.sort(key=lambda item: (item.follow_up_on or "9999", item.company.lower()))
    return ProspectListOut(items=items, summary=_summary(items))


def create_prospect(user_id: str, payload: ProspectIn) -> ProspectOut:
    stamp = _now()
    row = ProspectRow(id=uuid.uuid4().hex, user_id=user_id, created_at=stamp, updated_at=stamp)
    _apply(row, payload)
    with session_scope() as session:
        session.add(row)
        session.flush()
        return _out(row)


def _owned(session: Session, user_id: str, prospect_id: str) -> ProspectRow | None:
    row = session.get(ProspectRow, prospect_id)
    return row if row is not None and row.user_id == user_id else None


def update_prospect(user_id: str, prospect_id: str, payload: ProspectIn) -> ProspectOut | None:
    with session_scope() as session:
        row = _owned(session, user_id, prospect_id)
        if row is None:
            return None
        _apply(row, payload)
        row.updated_at = _now()
        session.flush()
        return _out(row)


def delete_prospect(user_id: str, prospect_id: str) -> bool:
    with session_scope() as session:
        row = _owned(session, user_id, prospect_id)
        if row is None:
            return False
        session.delete(row)
        return True


def _read_legacy_text(path: Path) -> str:
    """L'ancien code écrivait sans préciser l'encodage : UTF-8 sur Mac et Linux, cp1252 sous Windows."""
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def import_legacy_file(path: Path | None = None) -> int:
    """Reprend data/prospects.json dans la base, puis renomme le fichier.

    Seuls les prospects de comptes qui existent en base sont repris : les autres comptes
    vivaient en mémoire et ont disparu au redémarrage.
    """
    path = path or LEGACY_PATH
    if not path.exists():
        return 0
    try:
        raw = json.loads(_read_legacy_text(path))
    except (OSError, ValueError) as error:
        # Ne pas bloquer le démarrage : le fichier reste en place pour un nouvel essai.
        logger.error("Import de %s impossible : %s", path.name, error)
        return 0
    imported = 0
    with session_scope() as session:
        for user_id, items in (raw.items() if isinstance(raw, dict) else []):
            if session.get(UserRow, user_id) is None:
                continue
            for item in items:
                payload = ProspectIn.model_validate(item)
                created = datetime.fromisoformat(item["createdAt"]) if item.get("createdAt") else _now()
                updated = datetime.fromisoformat(item["updatedAt"]) if item.get("updatedAt") else created
                prospect_id = item.get("id") or uuid.uuid4().hex
                # Le fichier fait foi : il écrase la version d'exemple créée au démarrage.
                row = session.get(ProspectRow, prospect_id)
                if row is None:
                    row = ProspectRow(id=prospect_id, user_id=user_id)
                    session.add(row)
                row.created_at = created
                row.updated_at = updated
                _apply(row, payload)
                imported += 1
    path.rename(path.with_suffix(".json.imported"))
    logger.info("%s prospects repris depuis %s", imported, path.name)
    return imported
