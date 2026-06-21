"""Endpoints de sesión conversacional + adjuntos (multipart)."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.session_service import estimate_in_session
from app.sessions import ProjectMetadata, create_session, get_session

router = APIRouter(tags=["sessions"])


class CreateSessionResponse(BaseModel):
    session_id: str


class SessionEstimationResponse(BaseModel):
    text: str
    prompt_version: str
    project_metadata: ProjectMetadata


@router.post("/sessions", response_model=CreateSessionResponse)
def create():
    session = create_session()
    return CreateSessionResponse(session_id=session.session_id)


@router.post("/sessions/{session_id}/estimate", response_model=SessionEstimationResponse)
async def estimate(
    session_id: str,
    transcript: str = Form(...),
    attachments: list[UploadFile] = File(default=[]),
):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    files: list[tuple[str, bytes]] = []
    for f in attachments:
        files.append((f.filename, await f.read()))

    try:
        text = estimate_in_session(session, transcript, files)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - error del proveedor LLM
        raise HTTPException(status_code=502, detail=f"Error al generar la estimación: {exc}")

    return SessionEstimationResponse(
        text=text,
        prompt_version="v1",
        project_metadata=session.metadata,
    )
