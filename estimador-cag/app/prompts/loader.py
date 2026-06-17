"""Loader de prompts: único punto donde Python toca los templates Jinja2.

`render_estimation_prompt(request, version)` devuelve `(system, user)` listos para
enviar al modelo. Cambiar de versión es cambiar el argumento `version`, sin tocar
el resto del código.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.schemas import EstimationRequest

PROMPTS_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=False,
    undefined=StrictUndefined,
)


def render_estimation_prompt(
    request: EstimationRequest,
    version: str = "v1",
) -> tuple[str, str]:
    system = _env.get_template(f"estimation/{version}/system.j2")
    user = _env.get_template(f"estimation/{version}/user.j2")

    context = {
        "project_type": request.project_type.value,
        "detail_level": request.detail_level.value,
        "output_format": request.output_format.value,
        "description": request.description,
    }

    return system.render(**context), user.render(**context)


def render_session_estimation_prompt(
    metadata,
    transcript: str,
    version: str = "v1",
) -> tuple[str, str]:
    """Compone (system, user) para la estimación conversacional, inyectando el
    project_metadata en el system prompt y el transcript en el user prompt.

    `metadata` es un ProjectMetadata (se usa su .model_dump()).
    """
    system = _env.get_template(f"session_estimation/{version}/system.j2")
    user = _env.get_template(f"session_estimation/{version}/user.j2")

    context = {**metadata.model_dump(), "transcript": transcript}
    return system.render(**context), user.render(**context)
