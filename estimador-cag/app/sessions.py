"""Estado de sesión en memoria del proceso (sin BBDD).

Volatilidad aceptada en esta fase: si el proceso del servicio se reinicia, las
sesiones se pierden. Es suficiente para validar memoria conversacional dentro de
una sesión; la persistencia (Redis/BBDD) es de sesiones posteriores.

Distinción clave:
- `ConversationHistory` = el array de mensajes (user/assistant) que viaja al LLM,
  gestionado con ventana deslizante.
- `ProjectMetadata` = los hechos del proyecto en curso, que se preservan aparte y
  se inyectan en el system prompt en cada turno.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel

MAX_TURNS = 6  # pares user+assistant conservados por la ventana deslizante


class ProjectMetadata(BaseModel):
    project_name: str | None = None
    assumed_team_size: int | None = None
    mentioned_technologies: list[str] = []
    agreed_scope: str | None = None


@dataclass
class ConversationHistory:
    """Historial con ventana deslizante. El system prompt NO se guarda aquí: es
    invariante y se regenera en cada llamada a partir del ProjectMetadata actual."""

    max_turns: int = MAX_TURNS
    _messages: list[dict] = field(default_factory=list)

    def add_turn(self, user_content: str, assistant_content: str) -> None:
        self._messages.append({"role": "user", "content": user_content})
        self._messages.append({"role": "assistant", "content": assistant_content})
        self._trim()

    def _trim(self) -> None:
        max_msgs = self.max_turns * 2
        if len(self._messages) > max_msgs:
            self._messages = self._messages[-max_msgs:]

    def windowed_messages(self) -> list[dict]:
        return list(self._messages[-self.max_turns * 2 :])

    def to_messages_list(self, new_user_content: str) -> list[dict]:
        """Ventana de turnos previos + el nuevo mensaje de usuario."""
        return self.windowed_messages() + [{"role": "user", "content": new_user_content}]


@dataclass
class Session:
    session_id: str
    history: ConversationHistory = field(default_factory=ConversationHistory)
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    # Observabilidad por turno (Bloque 1 del stress test). El runner las lee vía
    # GET /sessions/{id} sin tener que parsear logs.
    turn_count: int = 0
    last_turn_observed: dict | None = None


_SESSIONS: dict[str, Session] = {}


def create_session() -> Session:
    session = Session(session_id=str(uuid.uuid4()))
    _SESSIONS[session.session_id] = session
    return session


def get_session(session_id: str) -> Session | None:
    return _SESSIONS.get(session_id)
