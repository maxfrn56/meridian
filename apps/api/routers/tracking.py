from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from models.schemas import ProgressOut, RunIn, TrackingOut
from routers.deps import current_user, current_workspace
from services.metrics import build_tracking
from services.orchestrator import run_tracking, tracking_plan
from services.progress import begin, snapshot
from store import User, Workspace

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("", response_model=TrackingOut)
def list_tracking(workspace: Workspace = Depends(current_workspace)) -> TrackingOut:
    return build_tracking(workspace)


@router.get("/progress", response_model=ProgressOut)
def read_progress(user: User = Depends(current_user)) -> ProgressOut:
    current = snapshot(user.id)
    return ProgressOut(
        running=current.running,
        done=current.done,
        total=current.total,
        percent=current.percent,
        label=current.label,
    )


@router.post("/run", response_model=ProgressOut)
async def run(payload: RunIn, background: BackgroundTasks, user: User = Depends(current_user)) -> ProgressOut:
    if snapshot(user.id).running:
        raise HTTPException(status_code=409, detail="Un suivi est déjà en cours.")
    providers = list(payload.providers) if payload.providers else None
    try:
        _workspace, _queries, _selected, steps = tracking_plan(user.id, payload.query_ids, providers)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    begin(user.id, steps)
    # La réponse part tout de suite : le suivi continue même si le navigateur lâche la requête.
    background.add_task(run_tracking, user.id, payload.query_ids, providers, True)
    current = snapshot(user.id)
    return ProgressOut(
        running=current.running,
        done=current.done,
        total=current.total,
        percent=current.percent,
        label=current.label,
    )
