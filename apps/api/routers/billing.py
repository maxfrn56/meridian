from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from models.schemas import CheckoutOut, SubscribeIn, SubscriptionOut
from routers.deps import current_user
from services.billing import activate, snapshot
from services.payments import PaymentError, apply_event, confirm_checkout, enabled, event_from, start_checkout
from store import User, store

router = APIRouter(prefix="/billing", tags=["billing"])


def _workspace_for(user: User):
    workspace = store.workspace_for(user.id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Espace introuvable.")
    return workspace


@router.get("", response_model=SubscriptionOut)
def read_subscription(user: User = Depends(current_user)) -> SubscriptionOut:
    return snapshot(_workspace_for(user))


@router.post("", response_model=SubscriptionOut)
def choose_plan(payload: SubscribeIn, user: User = Depends(current_user)) -> SubscriptionOut:
    if enabled():
        raise HTTPException(status_code=409, detail="Le forfait s'active après le paiement Stripe.")
    try:
        return activate(_workspace_for(user), payload.plan_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/checkout", response_model=CheckoutOut)
def open_checkout(payload: SubscribeIn, user: User = Depends(current_user)) -> CheckoutOut:
    try:
        url = start_checkout(_workspace_for(user), user.email, payload.plan_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PaymentError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return CheckoutOut(url=url)


@router.post("/confirm", response_model=SubscriptionOut)
def confirm_payment(
    user: User = Depends(current_user),
    session_id: str | None = Query(default=None, alias="sessionId"),
) -> SubscriptionOut:
    workspace = _workspace_for(user)
    try:
        found = confirm_checkout(workspace, session_id)
    except PaymentError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if not found:
        raise HTTPException(status_code=404, detail="Aucun paiement confirmé pour cet espace.")
    return snapshot(workspace)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    try:
        event = event_from(await request.body(), request.headers.get("stripe-signature", ""))
    except PaymentError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    apply_event(event)
    return {"received": True}
