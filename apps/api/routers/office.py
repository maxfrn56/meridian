from fastapi import APIRouter, Depends

from models.schemas import AdminOverviewOut
from routers.deps import current_admin
from services.office import overview
from store import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewOut)
def read_overview(_user: User = Depends(current_admin)) -> AdminOverviewOut:
    return overview()
