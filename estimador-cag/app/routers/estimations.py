"""Endpoint de estimación (interfaz de producto: parámetros tipados)."""

from fastapi import APIRouter, HTTPException

from app.schemas import EstimationRequest, EstimationResponse
from app.services.llm_service import run_estimation

router = APIRouter(tags=["estimations"])


@router.post("/estimate", response_model=EstimationResponse)
def estimate(request: EstimationRequest, prompt_version: str = "v1"):
    """Recibe parámetros tipados, compone el prompt y devuelve la estimación.

    `prompt_version` (query param) permite seleccionar la versión del prompt (bonus).
    """
    try:
        return run_estimation(request, version=prompt_version)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - error del proveedor LLM
        raise HTTPException(status_code=502, detail=f"Error al generar la estimación: {exc}")
