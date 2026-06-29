"""Logging estructurado mínimo (sin dependencias extra).

El ejercicio sugiere `structlog`, pero el proyecto no lo usa y no queremos sumar
una dependencia solo para esto. `log_event` emite una única línea JSON por la
librería estándar `logging`, fácil de filtrar con `grep turn_observed`.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("estimador.events")


def log_event(event: str, **fields) -> None:
    """Emite un evento estructurado como una sola línea JSON."""
    logger.info(json.dumps({"event": event, **fields}, default=str, ensure_ascii=False))
