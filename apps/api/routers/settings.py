from fastapi import APIRouter, Depends, HTTPException

from models.schemas import GenerateQuestionsIn, GenerateQuestionsOut, QueryOut, SettingsIn, SettingsOut
from routers.deps import current_workspace
from services.prompt_generator import GenerationError, generate_questions
from store import Workspace, store

router = APIRouter(prefix="/settings", tags=["settings"])


def _out(workspace: Workspace) -> SettingsOut:
    return SettingsOut(
        workspace_name=workspace.name,
        brand_name=workspace.brand_name,
        domain=workspace.domain,
        sector=workspace.sector,
        queries=[QueryOut(id=item.id, prompt=item.prompt, active=item.active, tag=item.tag) for item in workspace.queries],
        providers=list(workspace.providers),
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
            [(item.prompt, item.active, item.tag) for item in payload.queries],
            providers=payload.providers or None,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _out(updated)


@router.post("/queries/generate", response_model=GenerateQuestionsOut)
async def generate(payload: GenerateQuestionsIn, workspace: Workspace = Depends(current_workspace)) -> GenerateQuestionsOut:
    """Propose autant de questions que le forfait en envoie par jour. Rien n'est enregistré ici."""
    try:
        questions = await generate_questions(
            brand_name=payload.brand_name.strip(),
            domain=payload.domain.strip(),
            sector=payload.sector.strip(),
            existing=[item for item in payload.existing if item.strip()],
            plan_id=workspace.plan_id,
            trial_ends_at=workspace.trial_ends_at,
        )
    except GenerationError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return GenerateQuestionsOut(questions=questions)
