from fastapi import APIRouter, Depends

from models.schemas import OverviewOut
from routers.deps import current_workspace
from services.metrics import build_overview
from store import Workspace

router = APIRouter(tags=["overview"])


@router.get("/overview", response_model=OverviewOut)
def overview(workspace: Workspace = Depends(current_workspace)) -> OverviewOut:
    return build_overview(workspace)
