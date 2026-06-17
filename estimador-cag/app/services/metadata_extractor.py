"""Actualización de ProjectMetadata tras cada turno — extractor LLM.

Elegimos el extractor LLM (no una heurística regex) porque es más robusto ante
lenguaje natural variado: detecta nombre de proyecto, tecnologías y alcance aunque
se expresen de formas distintas, y en varios idiomas. Coste: una llamada extra
(barata) por turno. Si la extracción falla, se conserva la metadata actual.
"""

import json

from app.services.llm_service import complete
from app.sessions import ProjectMetadata

_EXTRACTOR_SYSTEM = """You extract structured project facts from a software estimation conversation.
Return ONLY a JSON object with exactly these keys:
- "project_name": string or null
- "assumed_team_size": integer or null
- "mentioned_technologies": array of strings (may be empty)
- "agreed_scope": string or null

Merge with the CURRENT metadata provided: keep known values unless the new turn
clearly changes them, and union the technologies. Do not invent facts. Output JSON only."""


def extract_metadata(
    current: ProjectMetadata, transcript: str, estimation: str
) -> ProjectMetadata:
    user = (
        f"CURRENT metadata (JSON):\n{current.model_dump_json()}\n\n"
        f"New transcript:\n{transcript}\n\n"
        f"Latest estimation:\n{estimation}\n\n"
        "Return the updated metadata as JSON."
    )
    try:
        raw = complete(_EXTRACTOR_SYSTEM, [{"role": "user", "content": user}], max_tokens=400)
        data = json.loads(_extract_json(raw))
    except Exception:
        return current

    merged = current.model_dump()
    for key in ("project_name", "assumed_team_size", "agreed_scope"):
        if data.get(key):
            merged[key] = data[key]
    techs = set(merged.get("mentioned_technologies") or [])
    techs.update(data.get("mentioned_technologies") or [])
    merged["mentioned_technologies"] = sorted(techs)

    try:
        return ProjectMetadata(**merged)
    except Exception:
        return current


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start : end + 1] if start != -1 and end != -1 else raw
