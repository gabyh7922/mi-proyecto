"""Endpoint de estimación (interfaz de producto: parámetros tipados)."""

from fastapi import APIRouter, HTTPException

from app.schemas.estimation import EstimationRequest, EstimationResponse
from app.services.llm_service import generate_estimation

router = APIRouter(tags=["estimations"])


@router.post("/estimate", response_model=EstimationResponse)
def estimate(body: EstimationRequest):
    try:
        return generate_estimation(body)
    except (RuntimeError, ValueError) as exc:
        # Errores de configuración (falta key / proveedor inválido)
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - error del proveedor LLM
        raise HTTPException(status_code=502, detail=f"Error al generar la estimación: {exc}")
