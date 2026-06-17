"""Endpoint de estimación."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import generate_estimation

router = APIRouter(tags=["estimations"])


class EstimationRequest(BaseModel):
    transcription: str = Field(
        ...,
        min_length=1,
        description="Texto de la transcripción de la reunión a estimar.",
        examples=[
            "En la reunión con el cliente se discutió la necesidad de una landing "
            "page con formulario de contacto e integración con su CRM..."
        ],
    )


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


@router.post("/estimate", response_model=EstimationResponse)
def estimate(body: EstimationRequest):
    if not body.transcription.strip():
        raise HTTPException(status_code=400, detail="La transcripción no puede estar vacía.")

    try:
        return generate_estimation(body.transcription)
    except (RuntimeError, ValueError) as exc:
        # Errores de configuración (falta key / proveedor inválido)
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - error del proveedor LLM
        raise HTTPException(status_code=502, detail=f"Error al generar la estimación: {exc}")
