"""Servicio de llamada al LLM (arquitectura CAG, interfaz de producto).

El prompt vive en el backend: se compone con `build_system_prompt(request)` a
partir de los parámetros tipados (EstimationRequest) y el contexto estático CAG.
El usuario solo aporta parámetros, no el prompt.

Patrón de mensajes:
    [system]    -> instrucciones (plantilla) + ejemplos de referencia (CAG)
    [user]      -> descripción del proyecto
    [assistant] -> (respuesta del modelo: la estimación)
"""

import time
from collections.abc import Iterator

from app.config import Settings, get_settings
from app.prompts.estimation import build_system_prompt, build_user_content
from app.schemas.estimation import EstimationRequest

# Precios por millón de tokens (USD) de los modelos económicos del ejercicio.
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def _build_result(estimation, model, provider, input_tokens, output_tokens) -> dict:
    prices = PRICING.get(model)
    cost = None
    if prices is not None:
        cost = round(
            (input_tokens / 1_000_000) * prices["input"]
            + (output_tokens / 1_000_000) * prices["output"],
            6,
        )
    return {
        "estimation": estimation,
        "model": model,
        "provider": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": cost,
    }


def generate_estimation(request: EstimationRequest) -> dict:
    """Genera una estimación (no streaming) a partir de parámetros tipados."""
    settings = get_settings()
    system_prompt = build_system_prompt(request)
    user_content = build_user_content(request)

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        return _build_result(
            estimation=response.choices[0].message.content,
            model=settings.openai_model,
            provider="openai",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return _build_result(
            estimation=response.content[0].text,
            model=settings.anthropic_model,
            provider="anthropic",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    raise ValueError(
        f"Proveedor no soportado: {settings.llm_provider!r}. Usa 'openai' o 'anthropic'."
    )


def stream_estimation(
    request: EstimationRequest,
    metadata: dict | None = None,
) -> Iterator[str]:
    """Genera la estimación en streaming (token a token) desde parámetros tipados.

    Va emitiendo fragmentos de texto. Si se pasa `metadata`, al terminar se rellena
    con: model, provider, input_tokens, output_tokens, elapsed_s.
    """
    settings = get_settings()
    system_prompt = build_system_prompt(request)
    user_content = build_user_content(request)
    start = time.time()

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
        if metadata is not None:
            metadata.update(
                model=settings.anthropic_model,
                provider="anthropic",
                input_tokens=final.usage.input_tokens,
                output_tokens=final.usage.output_tokens,
                elapsed_s=round(time.time() - start, 2),
            )
        return

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        stream = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            stream=True,
            stream_options={"include_usage": True},
        )
        usage = None
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            if getattr(chunk, "usage", None):
                usage = chunk.usage
        if metadata is not None:
            metadata.update(
                model=settings.openai_model,
                provider="openai",
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
                elapsed_s=round(time.time() - start, 2),
            )
        return

    raise ValueError(
        f"Proveedor no soportado: {settings.llm_provider!r}. Usa 'openai' o 'anthropic'."
    )
