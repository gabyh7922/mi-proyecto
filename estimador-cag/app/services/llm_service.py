"""Servicio de llamada al LLM (corazón de la arquitectura CAG).

El contexto estático (ejemplos de estimaciones previas) se inyecta directamente
en el system prompt: viaja en cada llamada, sin base de datos ni retrieval.

Patrón de mensajes:
    [system]    -> instrucciones + ejemplos de estimaciones previas
    [user]      -> transcripción de la reunión a estimar
    [assistant] -> (respuesta del modelo: la estimación)
"""

from app.config import Settings, get_settings
from app.context.examples import ESTIMATION_EXAMPLES

# Precios por millón de tokens (USD) de los modelos económicos del ejercicio.
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def _build_system_prompt() -> str:
    """Construye el system prompt inyectando los ejemplos de contexto (CAG)."""
    examples_text = "\n\n".join(
        f"### Ejemplo {i}\n"
        f"**Resumen de la reunión:**\n{ex['meeting_summary']}\n\n"
        f"**Estimación generada:**\n{ex['estimation']}"
        for i, ex in enumerate(ESTIMATION_EXAMPLES, start=1)
    )

    return f"""Eres un estimador de software senior con amplia experiencia en proyectos \
de desarrollo web, móvil y backend. Tu tarea es generar estimaciones de esfuerzo \
realistas a partir de la transcripción de una reunión con un cliente.

Cómo debes trabajar:
- Básate en los ejemplos de estimaciones previas que se incluyen más abajo: sigue \
su mismo formato, nivel de detalle y criterio.
- Desglosa el trabajo en tareas concretas con horas estimadas.
- Incluye un total de horas, el equipo recomendado y una duración estimada.
- Si la transcripción no aporta algún dato clave (alcance, plazos, integraciones), \
indica explícitamente los supuestos que estás asumiendo.
- Señala al menos un riesgo no obvio que el equipo suele pasar por alto.
- Responde en español y en formato Markdown, sin frases de relleno.

A continuación tienes tu base de conocimiento: estimaciones previas de referencia.

{examples_text}
"""


def _generate_openai(system_prompt: str, transcription: str, settings: Settings) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcription},
        ],
        temperature=0.3,
    )
    return _build_result(
        estimation=response.choices[0].message.content,
        model=settings.openai_model,
        provider="openai",
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )


def _generate_anthropic(system_prompt: str, transcription: str, settings: Settings) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": transcription}],
    )
    return _build_result(
        estimation=response.content[0].text,
        model=settings.anthropic_model,
        provider="anthropic",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


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


def generate_estimation(transcription: str) -> dict:
    """Genera una estimación de software a partir de una transcripción de reunión."""
    settings = get_settings()
    system_prompt = _build_system_prompt()

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
        return _generate_openai(system_prompt, transcription, settings)

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        return _generate_anthropic(system_prompt, transcription, settings)

    raise ValueError(
        f"Proveedor no soportado: {settings.llm_provider!r}. Usa 'openai' o 'anthropic'."
    )
