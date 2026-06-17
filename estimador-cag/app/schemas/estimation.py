"""Contratos de datos del estimador (request/response).

El frontend ya NO envía un mensaje de chat libre: envía parámetros tipados.
El prompt se compone en el backend a partir de estos parámetros (interfaz de
producto, no interfaz conversacional).
"""

from enum import Enum

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    MOBILE_APP = "mobile_app"
    WEB_SAAS = "web_saas"
    INTERNAL_TOOL = "internal_tool"
    DATA_PIPELINE = "data_pipeline"
    OTHER = "other"


class DetailLevel(str, Enum):
    SUMMARY = "summary"
    MEDIUM = "medium"
    DETAILED = "detailed"


class OutputFormat(str, Enum):
    PHASES_TABLE = "phases_table"
    LINE_ITEMS = "line_items"
    NARRATIVE = "narrative"


class EstimationRequest(BaseModel):
    description: str = Field(
        min_length=20,
        max_length=4000,
        description="Descripción del proyecto a estimar.",
    )
    project_type: ProjectType
    detail_level: DetailLevel = DetailLevel.MEDIUM
    output_format: OutputFormat = OutputFormat.PHASES_TABLE


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
