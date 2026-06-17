"""Plantilla de prompt versionada para el estimador (interfaz de producto).

El prompt es un artefacto de software: vive aquí (no en el textarea del usuario),
se versiona, se revisa y se testea. `build_system_prompt()` compone el system
prompt a partir de los parámetros tipados (EstimationRequest) inyectándolos en una
plantilla Jinja2, junto con el contexto estático CAG (ejemplos de referencia).
"""

from jinja2 import Template

from app.context.examples import ESTIMATION_EXAMPLES
from app.schemas.estimation import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)

PROMPT_VERSION = "estimation-v1"

# Traducciones legibles de los enums para el prompt.
PROJECT_TYPE_HUMAN = {
    ProjectType.MOBILE_APP: "aplicación móvil",
    ProjectType.WEB_SAAS: "plataforma web / SaaS",
    ProjectType.INTERNAL_TOOL: "herramienta interna",
    ProjectType.DATA_PIPELINE: "pipeline de datos",
    ProjectType.OTHER: "proyecto de software",
}

DETAIL_LEVEL_INSTRUCTION = {
    DetailLevel.SUMMARY: "Resumen de alto nivel: pocas líneas, sin desglose fino.",
    DetailLevel.MEDIUM: "Desglose moderado por tareas principales con horas.",
    DetailLevel.DETAILED: "Desglose granular y exhaustivo de cada tarea con horas.",
}

OUTPUT_FORMAT_INSTRUCTION = {
    OutputFormat.PHASES_TABLE: "Una tabla Markdown organizada por fases del proyecto.",
    OutputFormat.LINE_ITEMS: "Una lista de tareas (line items) con horas por tarea.",
    OutputFormat.NARRATIVE: "Texto en prosa, sin tablas ni listas.",
}

SYSTEM_TEMPLATE = Template(
    """\
Eres un estimador de software senior con más de 15 años de experiencia en \
proyectos de tipo {{ project_type_human }}. Tu tarea es generar una estimación \
de esfuerzo realista para el proyecto descrito por el usuario.

Cómo debes trabajar:
- Usa los ejemplos de estimaciones previas (más abajo) para calibrar precios, \
granularidad y estructura. Sé coherente con ellos.
- Incluye total de horas, equipo recomendado y duración estimada.
- Si falta algún dato clave (alcance, plazos, integraciones), indica los supuestos.
- Señala al menos un riesgo no obvio que los equipos suelen pasar por alto.
- Responde en español.

Nivel de detalle solicitado: {{ detail_instruction }}
Formato de salida solicitado: {{ output_instruction }}

===== ESTIMACIONES DE REFERENCIA =====
{{ examples_text }}
===== FIN DE ESTIMACIONES DE REFERENCIA =====
"""
)


def _examples_text() -> str:
    return "\n\n".join(
        f"--- Referencia {i} ---\n"
        f"Resumen de la reunión: {ex['meeting_summary']}\n"
        f"Estimación:\n{ex['estimation']}"
        for i, ex in enumerate(ESTIMATION_EXAMPLES, start=1)
    )


def build_system_prompt(request: EstimationRequest) -> str:
    """Compone el system prompt a partir de los parámetros tipados + contexto CAG."""
    return SYSTEM_TEMPLATE.render(
        project_type_human=PROJECT_TYPE_HUMAN[request.project_type],
        detail_instruction=DETAIL_LEVEL_INSTRUCTION[request.detail_level],
        output_instruction=OUTPUT_FORMAT_INSTRUCTION[request.output_format],
        examples_text=_examples_text(),
    ).strip()


def build_user_content(request: EstimationRequest) -> str:
    """El mensaje de usuario es la descripción del proyecto."""
    return request.description
