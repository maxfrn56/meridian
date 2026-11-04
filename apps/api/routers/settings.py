from fastapi import APIRouter, Depends, HTTPException

from models.schemas import CompetitorOut, QueryOut, SettingsIn, SettingsOut
from routers.deps import current_workspace
from store import Workspace, store

router = APIRouter(prefix="/settings", tags=["settings"])


def _out(workspace: Workspace) -> SettingsOut:
    return SettingsOut(
        workspace_name=workspace.name,
        brand_name=workspace.brand_name,
        domain=workspace.domain,
        sector=workspace.sector,
        competitors=[CompetitorOut(id=item.id, name=item.name, domain=item.domain) for item in workspace.competitors],
        queries=[QueryOut(id=item.id, prompt=item.prompt, active=item.active) for item in workspace.queries],
    )


@router.get("", response_model=SettingsOut)
def read_settings(workspace: Workspace = Depends(current_workspace)) -> SettingsOut:
    return _out(workspace)


@router.put("", response_model=SettingsOut)
def write_settings(payload: SettingsIn, workspace: Workspace = Depends(current_workspace)) -> SettingsOut:
    try:
        updated = store.update_settings(
            workspace.user_id,
            payload.workspace_name,
            payload.brand_name,
            payload.domain,
            payload.sector,
            [(item.name, item.domain) for item in payload.competitors],
            [(item.prompt, item.active) for item in payload.queries],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _out(updated)
