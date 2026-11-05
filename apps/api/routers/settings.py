import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from models.schemas import GenerateQuestionsIn, GenerateQuestionsOut, QueryOut, SettingsIn, SettingsOut
from routers.deps import current_workspace
from services.orchestrator import run_audit
from services.prompt_generator import GenerationError, generate_questions
from store import Workspace, store

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)


def _out(workspace: Workspace) -> SettingsOut:
    return SettingsOut(
        workspace_name=workspace.name,
        brand_name=workspace.brand_name,
        domain=workspace.domain,
        sector=workspace.sector,
        queries=[QueryOut(id=item.id, prompt=item.prompt, active=item.active) for item in workspace.queries],
    )


@router.get("", response_model=SettingsOut)
def read_settings(workspace: Workspace = Depends(current_workspace)) -> SettingsOut:
    return _out(workspace)


async def audit_in_background(user_id: str) -> None:
    """L'audit tourne après la réponse : un site lent ne bloque pas l'enregistrement."""
    try:
        await run_audit(user_id)
    except Exception as error:  # noqa: BLE001 - un échec se voit dans l'onglet Audit, il ne doit rien casser
        logger.warning("Audit automatique impossible : %s", error)


@router.put("", response_model=SettingsOut)
def write_settings(
    payload: SettingsIn,
    background: BackgroundTasks,
    workspace: Workspace = Depends(current_workspace),
) -> SettingsOut:
    try:
        updated = store.update_settings(
            workspace.user_id,
            payload.workspace_name,
            payload.brand_name,
            payload.domain,
            payload.sector,
            [(item.prompt, item.active) for item in payload.queries],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    # Nouveau domaine, ou aucun audit encore : on le lance sans attendre que le client y pense.
    if updated.domain and (updated.domain != workspace.domain or not workspace.audits):
        background.add_task(audit_in_background, workspace.user_id)
    return _out(updated)


@router.post("/queries/generate", response_model=GenerateQuestionsOut)
async def generate(payload: GenerateQuestionsIn, workspace: Workspace = Depends(current_workspace)) -> GenerateQuestionsOut:
    """Propose autant de questions que le forfait en envoie par mois. Rien n'est enregistré ici."""
    try:
        questions = await generate_questions(
            brand_name=payload.brand_name.strip(),
            domain=payload.domain.strip(),
            sector=payload.sector.strip(),
            existing=[item for item in payload.existing if item.strip()],
            plan_id=workspace.plan_id,
        )
    except GenerationError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return GenerateQuestionsOut(questions=questions)
