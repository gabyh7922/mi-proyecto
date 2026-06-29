"""Wrapper observable del LLM.

`complete()` (en `llm_service`) devolvía solo el texto. Para el stress test
necesitamos medir cada llamada: latencia, tokens de entrada/salida y coste.
`complete_observed()` envuelve la llamada al proveedor y devuelve un `LLMResult`
con todo eso. `llm_service.complete()` ahora delega aquí y se queda con `.text`,
así el resto del código (extractor de metadata, estimación por formulario) no
cambia.

`MODEL_COSTS` es la tabla de precios en USD por millón de tokens. Para el
ejercicio el proveedor es único (Anthropic / claude-haiku-4-5), así que la curva
de coste es comparable turno a turno.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.config import get_settings

# Precio en USD por 1.000.000 de tokens (input, output).
# Fuente: tabla de precios de los modelos al construir el ejercicio.
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


@dataclass
class LLMResult:
    """Resultado observable de una llamada al LLM."""

    text: str
    latency_ms: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    model: str
    provider: str

    def merge(self, other: "LLMResult | None") -> "LLMResult":
        """Suma dos llamadas en una sola observación de turno (estimación +
        extractor de metadata). La latencia se suma porque ambas son secuenciales
        dentro del mismo turno."""
        if other is None:
            return self
        return LLMResult(
            text=self.text,
            latency_ms=self.latency_ms + other.latency_ms,
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
            cost_usd=self.cost_usd + other.cost_usd,
            model=self.model,
            provider=self.provider,
        )


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """Coste en USD de una llamada dado el modelo y los tokens."""
    price = MODEL_COSTS.get(model)
    if price is None:
        return 0.0
    return tokens_in / 1_000_000 * price["input"] + tokens_out / 1_000_000 * price["output"]


def complete_observed(system: str, messages: list[dict], max_tokens: int = 1500) -> LLMResult:
    """Llama al LLM y mide latencia, tokens y coste de la llamada."""
    settings = get_settings()
    start = time.perf_counter()

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
        text = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        model = settings.openai_model
        provider = "openai"

    elif settings.llm_provider == "anthropic":
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
        text = response.content[0].text if response.content else ""
        usage = response.usage
        tokens_in = usage.input_tokens if usage else 0
        tokens_out = usage.output_tokens if usage else 0
        model = settings.anthropic_model
        provider = "anthropic"

    else:
        raise ValueError(
            f"Proveedor no soportado: {settings.llm_provider!r}. Usa 'openai' o 'anthropic'."
        )

    latency_ms = (time.perf_counter() - start) * 1000
    return LLMResult(
        text=text,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd(model, tokens_in, tokens_out),
        model=model,
        provider=provider,
    )
