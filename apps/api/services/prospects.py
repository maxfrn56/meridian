from __future__ import annotations

import json
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from models.schemas import ProspectIn, ProspectListOut, ProspectOut, ProspectSummary

PATH = Path(__file__).resolve().parents[1] / "data" / "prospects.json"
DEMO_USER = uuid.uuid5(uuid.NAMESPACE_DNS, "demo@geo.dev").hex
_LOCK = threading.RLock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed(user_id: str) -> list[dict]:
    if user_id != DEMO_USER:
        return []
    today = date.today()
    stamp = _now().isoformat()
    return [
        {
            "id": uuid.uuid5(uuid.NAMESPACE_URL, "purenat").hex,
            "company": "Purenat",
            "contactName": "Équipe Purenat",
            "email": "contact@pure-nat.com",
            "website": "https://www.pure-nat.com",
            "city": "Bayonne",
            "question": (
                "Comment faire baisser les COV dans une crèche ?\n"
                "Quel filtre détruit le formaldéhyde ?\n"
                "Quoi intégrer dans une centrale de traitement d’air ?"
            ),
            "channel": "email",
            "status": "envoye",
            "sentOn": today.isoformat(),
            "followUpOn": (today + timedelta(days=4)).isoformat(),
            "meetingOn": None,
            "amountEur": 1500,
            "nextStep": "Relancer si aucune réponse.",
            "notes": "Mail envoyé à contact@pure-nat.com. Trois questions d’acheteurs, sans statistique ni présentation d’outil.",
            "createdAt": stamp,
            "updatedAt": stamp,
        }
    ]


def _read() -> dict[str, list[dict]]:
    if not PATH.exists():
        return {}
    raw = json.loads(PATH.read_text())
    return raw if isinstance(raw, dict) else {}


def _write(data: dict[str, list[dict]]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _items(user_id: str) -> list[dict]:
    data = _read()
    items = data.get(user_id)
    if items is None:
        items = _seed(user_id)
        data[user_id] = items
        _write(data)
    return items


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
    with _LOCK:
        items = [ProspectOut.model_validate(item) for item in _items(user_id)]
    items.sort(key=lambda item: (item.follow_up_on or "9999", item.company.lower()))
    return ProspectListOut(items=items, summary=_summary(items))


def create_prospect(user_id: str, payload: ProspectIn) -> ProspectOut:
    stamp = _now().isoformat()
    record = payload.model_dump(by_alias=True)
    record.update(id=uuid.uuid4().hex, createdAt=stamp, updatedAt=stamp)
    with _LOCK:
        data = _read()
        items = data.get(user_id)
        if items is None:
            items = _seed(user_id)
        items.append(record)
        data[user_id] = items
        _write(data)
    return ProspectOut.model_validate(record)


def update_prospect(user_id: str, prospect_id: str, payload: ProspectIn) -> ProspectOut | None:
    with _LOCK:
        data = _read()
        items = data.get(user_id) or []
        for index, item in enumerate(items):
            if item.get("id") != prospect_id:
                continue
            record = payload.model_dump(by_alias=True)
            record.update(id=prospect_id, createdAt=item.get("createdAt") or _now().isoformat(), updatedAt=_now().isoformat())
            items[index] = record
            data[user_id] = items
            _write(data)
            return ProspectOut.model_validate(record)
    return None


def delete_prospect(user_id: str, prospect_id: str) -> bool:
    with _LOCK:
        data = _read()
        items = data.get(user_id) or []
        kept = [item for item in items if item.get("id") != prospect_id]
        if len(kept) == len(items):
            return False
        data[user_id] = kept
        _write(data)
        return True
