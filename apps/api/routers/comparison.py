from fastapi import APIRouter, Depends

from models.schemas import ComparisonOut
from routers.deps import current_workspace
from services.comparison import build_comparison
from store import Workspace

router = APIRouter(tags=["comparison"])


@router.get("/comparison", response_model=ComparisonOut)
def comparison(workspace: Workspace = Depends(current_workspace)) -> ComparisonOut:
    return build_comparison(workspace)
