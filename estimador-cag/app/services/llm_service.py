"""Servicio de estimación.

`complete()` es la llamada de bajo nivel al LLM (system + messages separados),
reutilizada por la estimación por formulario, el extractor de metadata y la
estimación conversacional. Abstrae el proveedor (OpenAI / Anthropic).
"""

from app.config import get_settings
from app.prompts.loader import render_estimation_prompt
from app.schemas import EstimationRequest, EstimationResponse


def complete(system: str, messages: list[dict], max_tokens: int = 1500) -> str:
    """Llama al LLM con `system` y una lista de `messages` (user/assistant)."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    raise ValueError(
        f"Proveedor no soportado: {settings.llm_provider!r}. Usa 'openai' o 'anthropic'."
    )


def run_estimation(request: EstimationRequest, version: str = "v1") -> EstimationResponse:
    """Estimación por formulario (parámetros tipados, Sesión 4)."""
    system, user = render_estimation_prompt(request, version=version)
    text = complete(system, [{"role": "user", "content": user}])
    return EstimationResponse(text=text, prompt_version=version)
