"""Orquestación de la estimación conversacional dentro de una sesión.

Flujo de cada turno:
1. Extraer texto de los adjuntos (Camino B) y concatenarlo al transcript.
2. Componer el system prompt con el project_metadata actual + el user prompt.
3. Llamar al LLM con la ventana deslizante del historial + el nuevo mensaje.
4. Guardar el turno (user, assistant) en el historial.
5. Actualizar el project_metadata con el extractor LLM.
"""

from app.prompts.loader import render_session_estimation_prompt
from app.services.attachments import build_attachments_text
from app.services.llm_service import complete
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

    text = complete(system, messages, max_tokens=1500)

    session.history.add_turn(user, text)
    session.metadata = extract_metadata(session.metadata, full_input, text)
    return text
