from typing import Literal

from fastapi import APIRouter, Depends, Query

from models.schemas import ComparisonOut
from routers.deps import current_workspace
from services.comparison import build_comparison
from store import Workspace

router = APIRouter(tags=["comparison"])


@router.get("/comparison", response_model=ComparisonOut)
def comparison(
    span: Literal["week", "all"] = Query(default="week"),
    tag: str = Query(default="", max_length=40),
    workspace: Workspace = Depends(current_workspace),
) -> ComparisonOut:
    return build_comparison(workspace, span=span, tag=tag)
