"""Orquestación de la estimación conversacional dentro de una sesión.

Flujo de cada turno:
1. Extraer texto de los adjuntos (Camino B) y concatenarlo al transcript.
2. Componer el system prompt con el project_metadata actual + el user prompt.
3. Llamar al LLM con la ventana deslizante del historial + el nuevo mensaje.
4. Guardar el turno (user, assistant) en el historial.
5. Actualizar el project_metadata con el extractor LLM.

Bloque 1 del stress test: justo antes del `return` emitimos un único evento
`turn_observed` con todo lo medible del turno, y lo dejamos también en
`session.last_turn_observed` para que el runner lo lea por HTTP. Un evento
agregado evita tener que reconciliar cinco logs sueltos y sus timestamps; con él
una pasada produce el CSV y la correlación (p. ej. messages_in_window vs
cost_usd) es trivial.
"""

from app.observability import log_event
from app.prompts.loader import render_session_estimation_prompt
from app.services.attachments import build_attachments_text
from app.services.llm_wrapper import complete_observed
from app.services.metadata_extractor import extract_metadata
from app.sessions import Session


def estimate_in_session(
    session: Session,
    transcript: str,
    attachments: list[tuple[str, bytes]] | None = None,
    version: str = "v1",
) -> str:
    attachments_text = build_attachments_text(attachments or [])
    full_input = transcript
    if attachments_text:
        full_input = f"{transcript}\n\n{attachments_text}"

    system, user = render_session_estimation_prompt(
        session.metadata, full_input, version=version
    )
    messages = session.history.to_messages_list(user)

    result = complete_observed(system, messages, max_tokens=1500)
    text = result.text

    session.history.add_turn(user, text)
    session.metadata, extractor_result = extract_metadata(session.metadata, full_input, text)

    # Coste real del turno = estimación + extractor de metadata (dos llamadas).
    turn = result.merge(extractor_result)
    session.turn_count += 1

    observation = {
        "turn_index": session.turn_count,
        "session_id": session.session_id,
        "enriched_transcript_chars": len(full_input),
        "attachments_total_chars": len(attachments_text),
        "messages_in_window": len(session.history.windowed_messages()),
        # Este CAG no implementa anclas heurísticas separadas ni un summarizer de
        # texto: la memoria que sobrevive a la ventana es ProjectMetadata. Por eso
        # anchors_count=0 y summary_chars = tamaño del ProjectMetadata serializado.
        "anchors_count": 0,
        "summary_chars": len(session.metadata.model_dump_json()),
        "tokens_in": turn.tokens_in,
        "tokens_out": turn.tokens_out,
        "cost_usd": turn.cost_usd,
        "latency_ms": turn.latency_ms,
        # Sin caché (exact/semantic) en este baseline y sin tiers dinámicos.
        "cache_hit_kind": "none",
        "last_resolved_tier": None,
        "model": turn.model,
        "provider": turn.provider,
    }
    session.last_turn_observed = observation
    log_event("turn_observed", **observation)

    return text
