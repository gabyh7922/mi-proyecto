"""Servicio de estimación.

Compone el prompt con la plantilla Jinja2 versionada (render_estimation_prompt) y
llama al LLM pasando `system` y `user` como mensajes SEPARADOS. Devuelve un
EstimationResponse(text, prompt_version). La respuesta sigue siendo texto libre
(la estructuraremos en el directo).
"""

from app.config import get_settings
from app.prompts.loader import render_estimation_prompt
from app.schemas import EstimationRequest, EstimationResponse


def run_estimation(request: EstimationRequest, version: str = "v1") -> EstimationResponse:
    settings = get_settings()
    system, user = render_estimation_prompt(request, version=version)

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        text = response.choices[0].message.content

    elif settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text

    else:
        raise ValueError(
            f"Proveedor no soportado: {settings.llm_provider!r}. Usa 'openai' o 'anthropic'."
        )

    return EstimationResponse(text=text, prompt_version=version)
