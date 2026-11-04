from fastapi import APIRouter, Depends, HTTPException

from models.schemas import AuditResponse, AuditRunIn
from routers.deps import current_user, current_workspace
from services.metrics import build_audit
from services.orchestrator import run_audit
from store import User, Workspace, store

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditResponse)
def latest(workspace: Workspace = Depends(current_workspace)) -> AuditResponse:
    return build_audit(workspace)


@router.post("/run", response_model=AuditResponse)
async def run(payload: AuditRunIn, user: User = Depends(current_user)) -> AuditResponse:
    try:
        await run_audit(user.id, payload.url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    workspace = store.workspace_for(user.id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Espace introuvable.")
    return build_audit(workspace)
