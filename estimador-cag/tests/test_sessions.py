"""Tests de la sesión conversacional (Paso 7).

Las llamadas al LLM se mockean (monkeypatch) para que los tests sean rápidos,
deterministas y sin coste de API. Verifican el cableado: actualización de
project_metadata, que el adjunto llega al prompt, y la ventana deslizante.
"""

from io import BytesIO

import httpx
import pytest
from docx import Document
from httpx import ASGITransport

import app.services.session_service as session_service
from app.main import app
from app.sessions import ConversationHistory, ProjectMetadata


def _make_docx(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# --- Test 1: dos peticiones enlazadas actualizan project_metadata ---
async def test_metadata_updates_across_two_turns(monkeypatch):
    monkeypatch.setattr(session_service, "complete", lambda *a, **k: "ESTIMATE: 100h")

    def fake_extract(current: ProjectMetadata, transcript, estimation):
        techs = current.mentioned_technologies + [f"Tech{len(current.mentioned_technologies) + 1}"]
        return ProjectMetadata(
            project_name="DemoProject",
            assumed_team_size=(current.assumed_team_size or 0) + 1,
            mentioned_technologies=techs,
            agreed_scope=current.agreed_scope,
        )

    monkeypatch.setattr(session_service, "extract_metadata", fake_extract)

    async with _client() as client:
        sid = (await client.post("/api/v1/sessions")).json()["session_id"]

        r1 = (await client.post(f"/api/v1/sessions/{sid}/estimate",
                                data={"transcript": "Mobile booking app"})).json()
        assert r1["project_metadata"]["project_name"] == "DemoProject"
        assert r1["project_metadata"]["assumed_team_size"] == 1

        r2 = (await client.post(f"/api/v1/sessions/{sid}/estimate",
                                data={"transcript": "Add Stripe payments"})).json()
        # La metadata se acumula entre turnos (memoria persistente en la sesión)
        assert r2["project_metadata"]["assumed_team_size"] == 2
        assert len(r2["project_metadata"]["mentioned_technologies"]) == 2


# --- Test 2: el contenido de un adjunto influye en el prompt enviado al LLM ---
async def test_attachment_content_reaches_prompt(monkeypatch):
    captured = {}

    def fake_complete(system, messages, max_tokens=1500):
        captured["messages"] = messages
        return "ESTIMATE based on attachment"

    monkeypatch.setattr(session_service, "complete", fake_complete)
    monkeypatch.setattr(session_service, "extract_metadata", lambda current, *a, **k: current)

    docx_bytes = _make_docx("SECRET_REQUIREMENT: must integrate with SAP")

    async with _client() as client:
        sid = (await client.post("/api/v1/sessions")).json()["session_id"]
        resp = await client.post(
            f"/api/v1/sessions/{sid}/estimate",
            data={"transcript": "Estimate this internal tool"},
            files=[("attachments", ("spec.docx", docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
        assert resp.status_code == 200

    last_user_msg = captured["messages"][-1]["content"]
    assert "SECRET_REQUIREMENT: must integrate with SAP" in last_user_msg
    assert "--- attachment: spec.docx ---" in last_user_msg


# --- Test 3: la ventana deslizante nunca supera MAX_TURNS ---
def test_sliding_window_caps_history():
    history = ConversationHistory(max_turns=6)
    for i in range(8):  # 8 turnos
        history.add_turn(f"user {i}", f"assistant {i}")

    windowed = history.windowed_messages()
    assert len(windowed) == 6 * 2  # 6 pares = 12 mensajes
    # conserva los más recientes
    assert windowed[-1]["content"] == "assistant 7"
    assert windowed[0]["content"] == "user 2"
    # el array que viaja al LLM = ventana + nuevo user
    assert len(history.to_messages_list("nuevo")) == 6 * 2 + 1
