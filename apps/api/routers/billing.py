from fastapi import APIRouter, Depends, HTTPException

from models.schemas import SubscribeIn, SubscriptionOut
from routers.deps import current_workspace
from services.billing import activate, snapshot
from store import Workspace

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("", response_model=SubscriptionOut)
def read_subscription(workspace: Workspace = Depends(current_workspace)) -> SubscriptionOut:
    return snapshot(workspace)


@router.post("", response_model=SubscriptionOut)
def choose_plan(payload: SubscribeIn, workspace: Workspace = Depends(current_workspace)) -> SubscriptionOut:
    try:
        return activate(workspace, payload.plan_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
