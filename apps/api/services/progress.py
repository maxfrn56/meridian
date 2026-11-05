"""Avancement du suivi en cours, pour la barre affichée au client.

L'état vit dans le process qui exécute le suivi. Une autre requête du même
process peut le lire pendant que les moteurs répondent.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class RunProgress:
    running: bool
    done: int
    total: int
    percent: int
    label: str


@dataclass
class _State:
    done: int
    total: int
    label: str


_runs: dict[str, _State] = {}
_done: dict[str, RunProgress] = {}
_guard = threading.Lock()
_IDLE = RunProgress(running=False, done=0, total=0, percent=0, label="")


def _percent(done: int, total: int) -> int:
    if total <= 0:
        return 0
    return min(100, round(done * 100 / total))


def begin(user_id: str, total: int) -> None:
    count = max(total, 1)
    with _guard:
        _done.pop(user_id, None)
        _runs[user_id] = _State(done=0, total=count, label=f"0 sur {count}")


def advance(user_id: str, detail: str) -> None:
    with _guard:
        state = _runs.get(user_id)
        if state is None:
            return
        state.done = min(state.total, state.done + 1)
        state.label = f"{state.done} sur {state.total} · {detail}"


def retitle(user_id: str, label: str) -> None:
    with _guard:
        state = _runs.get(user_id)
        if state is None:
            return
        state.label = label


def finish(user_id: str, error: str = "") -> None:
    with _guard:
        state = _runs.pop(user_id, None)
        if state is None and not error:
            return
        done = state.done if state else 0
        total = state.total if state else 0
        _done[user_id] = RunProgress(
            running=False,
            done=total if not error else done,
            total=total,
            percent=100 if not error else _percent(done, total),
            label=error or "Suivi terminé.",
        )


def snapshot(user_id: str) -> RunProgress:
    with _guard:
        state = _runs.get(user_id)
        if state is not None:
            return RunProgress(
                running=True,
                done=state.done,
                total=state.total,
                percent=_percent(state.done, state.total),
                label=state.label,
            )
        return _done.get(user_id, _IDLE)
