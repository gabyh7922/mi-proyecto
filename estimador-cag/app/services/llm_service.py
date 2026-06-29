"""Servicio de estimación.

`complete()` es la llamada de bajo nivel al LLM (system + messages separados),
reutilizada por la estimación por formulario, el extractor de metadata y la
estimación conversacional. Abstrae el proveedor (OpenAI / Anthropic).

La lógica del proveedor + la instrumentación (latencia, tokens, coste) viven en
`llm_wrapper.complete_observed()`. `complete()` delega ahí y se queda solo con el
texto, para que el código que no necesita métricas siga igual.
"""

from app.prompts.loader import render_estimation_prompt
from app.schemas import EstimationRequest, EstimationResponse
from app.services.llm_wrapper import complete_observed


def complete(system: str, messages: list[dict], max_tokens: int = 1500) -> str:
    """Llama al LLM con `system` y una lista de `messages` (user/assistant)."""
    return complete_observed(system, messages, max_tokens=max_tokens).text


def run_estimation(request: EstimationRequest, version: str = "v1") -> EstimationResponse:
    """Estimación por formulario (parámetros tipados, Sesión 4)."""
    system, user = render_estimation_prompt(request, version=version)
    text = complete(system, [{"role": "user", "content": user}])
    return EstimationResponse(text=text, prompt_version=version)
