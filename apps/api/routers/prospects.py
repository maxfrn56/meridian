from fastapi import APIRouter, Depends, HTTPException, Response

from models.schemas import ProspectIn, ProspectListOut, ProspectOut
from routers.deps import current_user
from services.prospects import create_prospect, delete_prospect, list_prospects, update_prospect
from store import User

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.get("", response_model=ProspectListOut)
def read_prospects(user: User = Depends(current_user)) -> ProspectListOut:
    return list_prospects(user.id)


@router.post("", response_model=ProspectOut, status_code=201)
def add_prospect(payload: ProspectIn, user: User = Depends(current_user)) -> ProspectOut:
    return create_prospect(user.id, payload)


@router.put("/{prospect_id}", response_model=ProspectOut)
def edit_prospect(prospect_id: str, payload: ProspectIn, user: User = Depends(current_user)) -> ProspectOut:
    updated = update_prospect(user.id, prospect_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Prospect introuvable.")
    return updated


@router.delete("/{prospect_id}", status_code=204)
def remove_prospect(prospect_id: str, user: User = Depends(current_user)) -> Response:
    if not delete_prospect(user.id, prospect_id):
        raise HTTPException(status_code=404, detail="Prospect introuvable.")
    return Response(status_code=204)
