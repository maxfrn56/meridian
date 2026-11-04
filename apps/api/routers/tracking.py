from fastapi import APIRouter, Depends, HTTPException

from models.schemas import RunIn, TrackingOut
from routers.deps import current_user, current_workspace
from services.metrics import build_tracking
from services.orchestrator import run_tracking
from store import User, Workspace, store

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("", response_model=TrackingOut)
def list_tracking(workspace: Workspace = Depends(current_workspace)) -> TrackingOut:
    return build_tracking(workspace)


@router.post("/run", response_model=TrackingOut)
async def run(payload: RunIn, user: User = Depends(current_user)) -> TrackingOut:
    try:
        await run_tracking(user.id, payload.query_ids, list(payload.providers) if payload.providers else None)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    workspace = store.workspace_for(user.id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Espace introuvable.")
    return build_tracking(workspace)
