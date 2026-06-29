"""Bloque 5 — Runner del stress test.

Orquesta dos fases que aíslan las dos dimensiones de estrés del CAG:

- Fase ``multiturn``: cada escenario (growing/pivot/contradiction) se ejecuta a
  fondo SIN adjunto. Una fila por turno -> de aquí salen las curvas
  coste-acumulado-vs-turno y recall-vs-N (el barrido N in {1,3,6,10,20} es,
  simplemente, leer la fila de cada turn_index).
- Fase ``attachments``: una misma estimación inicial corta con un adjunto de
  tamaño creciente {0,5,20,50,100} KB. De aquí salen latencia/coste/recall vs
  tamaño del adjunto.

Se decide leer ``turn_observed`` por HTTP (``GET /sessions/{id}`` con el último
turno embebido) en vez de parsear stdout del estimador: es robusto, no depende
del formato del log y funciona igual in-process y contra un servidor real.

Modos:
- por defecto, in-process (httpx + ASGITransport) -> no hace falta levantar nada.
- ``--http http://localhost:8000`` golpea un servidor real.
- ``--fake`` (solo in-process) sustituye el LLM por un stub determinista para
  validar el cableado del harness sin gastar API.

Ejemplo:

    uv run python -m evals.stress.run --scenarios growing,pivot,contradiction \\
        --attachment-sizes 0,5,20,50,100 --repeats 3 --output evals/stress/results.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

import httpx
from httpx import ASGITransport

from evals.stress.fixtures.build_pdfs import MARKER, build_all
from evals.stress.metrics import CostBudgetMetric, LatencyBudgetMetric, MemoryDriftMetric
from evals.stress.scenarios import SCENARIOS

API = "/api/v1"

# Presupuestos = contratos de diseño (SLA del cliente convertido en test).
LATENCY_BUDGET_MS = 4000
COST_BUDGET_USD = 0.01

# Transcript fijo para la fase de adjuntos: obliga al modelo a apoyarse en el doc.
ATTACHMENT_TRANSCRIPT = (
    "Estimate this internal tool. Base the scope strictly on the attached "
    "requirements document and call out its critical requirement."
)

CSV_COLUMNS = [
    "scenario", "phase", "attachment_kb", "repeat", "turn_index", "session_id",
    "enriched_transcript_chars", "attachments_total_chars", "messages_in_window",
    "anchors_count", "summary_chars", "tokens_in", "tokens_out", "cost_usd",
    "latency_ms", "cache_hit_kind", "last_resolved_tier", "model", "provider",
    "attachment_marker_recall", "first_fact_recall", "memory_drift_recall",
    "latency_budget_pass", "cost_budget_pass", "error",
]


def _build_snapshot_for_drift(project_metadata: dict) -> dict:
    """Snapshot que consume MemoryDriftMetric. En este CAG la memoria que
    sobrevive a la ventana es ProjectMetadata; summary/anchors van vacíos."""
    return {"summary": "", "anchors": [], "metadata": project_metadata}


async def _run_turn(
    client: httpx.AsyncClient,
    session_id: str,
    transcript: str,
    attachment: tuple[str, bytes] | None,
    *,
    scenario_name: str,
    phase: str,
    attachment_kb: int,
    repeat: int,
    facts_before,
    first_fact: str | None,
) -> dict:
    """Ejecuta un turno, lee el snapshot y evalúa las métricas. Devuelve la fila."""
    files = None
    if attachment is not None:
        files = [("attachments", (attachment[0], attachment[1], "application/pdf"))]

    row = {c: "" for c in CSV_COLUMNS}
    row.update(scenario=scenario_name, phase=phase, attachment_kb=attachment_kb, repeat=repeat)

    try:
        resp = await client.post(
            f"{API}/sessions/{session_id}/estimate",
            data={"transcript": transcript},
            files=files,
            timeout=120.0,
        )
        if resp.status_code != 200:
            row["error"] = f"HTTP {resp.status_code}: {resp.text[:160]}"
            return row
        resp_text = resp.json().get("text", "")

        snap = (await client.get(f"{API}/sessions/{session_id}", timeout=30.0)).json()
        obs = snap.get("last_turn_observed") or {}
        metadata = snap.get("project_metadata") or {}
    except Exception as exc:  # noqa: BLE001 - registramos el fallo como dato
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    # Campos de turn_observed
    for key in (
        "turn_index", "enriched_transcript_chars", "attachments_total_chars",
        "messages_in_window", "anchors_count", "summary_chars", "tokens_in",
        "tokens_out", "cost_usd", "latency_ms", "cache_hit_kind",
        "last_resolved_tier", "model", "provider",
    ):
        if obs.get(key) is not None:
            row[key] = obs[key]
    row["session_id"] = session_id

    # Métricas de presupuesto (Bloque 4)
    row["latency_budget_pass"] = int(LatencyBudgetMetric(LATENCY_BUDGET_MS).evaluate(obs).passed)
    row["cost_budget_pass"] = int(CostBudgetMetric(COST_BUDGET_USD).evaluate(obs).passed)

    # Recall del marcador del adjunto en la respuesta
    if attachment_kb > 0:
        row["attachment_marker_recall"] = int(MARKER.lower() in resp_text.lower())

    # Memory drift sobre el snapshot
    drift_snap = _build_snapshot_for_drift(metadata)
    if facts_before:
        scores = [MemoryDriftMetric(t.fact).evaluate(drift_snap).score for t in facts_before]
        row["memory_drift_recall"] = round(sum(scores) / len(scores), 3)
    if first_fact is not None and obs.get("turn_index", 0) > 1:
        row["first_fact_recall"] = int(MemoryDriftMetric(first_fact).evaluate(drift_snap).passed)

    return row


async def _create_session(client: httpx.AsyncClient) -> str:
    resp = await client.post(f"{API}/sessions", timeout=30.0)
    return resp.json()["session_id"]


async def run(
    client: httpx.AsyncClient,
    scenario_names: list[str],
    attachment_sizes: list[int],
    repeats: int,
    max_turns: int,
    phases: list[str],
) -> list[dict]:
    rows: list[dict] = []
    pdfs = build_all() if any(s > 0 for s in attachment_sizes) else {}

    # --- Fase multiturn (sin adjunto) ---
    if "multiturn" in phases:
        for name in scenario_names:
            scenario = SCENARIOS[name]
            first_fact = scenario.turns[0].fact
            for repeat in range(repeats):
                sid = await _create_session(client)
                for turn in scenario.turns_through(max_turns):
                    rows.append(await _run_turn(
                        client, sid, turn.transcript, None,
                        scenario_name=name, phase="multiturn", attachment_kb=0,
                        repeat=repeat, facts_before=scenario.facts_before(turn.turn_index),
                        first_fact=first_fact,
                    ))
                    print(f"  [multiturn] {name} r{repeat} turn {turn.turn_index} ok")

    # --- Fase attachments (una estimación inicial por tamaño) ---
    if "attachments" in phases:
        for kb in attachment_sizes:
            attachment = None
            if kb > 0:
                p = pdfs[kb]
                attachment = (p.name, p.read_bytes())
            for repeat in range(repeats):
                sid = await _create_session(client)
                rows.append(await _run_turn(
                    client, sid, ATTACHMENT_TRANSCRIPT, attachment,
                    scenario_name="attachment", phase="attachments", attachment_kb=kb,
                    repeat=repeat, facts_before=[], first_fact=None,
                ))
                print(f"  [attachments] {kb}KB r{repeat} ok")

    return rows


def _install_fake_llm() -> None:
    """Stub determinista del LLM para validar el harness sin gastar API.
    Solo tiene efecto en modo in-process (mismo proceso Python)."""
    import app.services.metadata_extractor as me
    import app.services.session_service as ss
    from app.services.llm_wrapper import LLMResult, cost_usd

    def fake(system, messages, max_tokens=1500):
        chars = len(system) + sum(len(m.get("content", "")) for m in messages)
        tokens_in = chars // 4
        tokens_out = min(max_tokens, 400)
        # Texto que incluye el marcador si el adjunto venía en el prompt.
        text = "ESTIMATE: ~120h. " + (MARKER if MARKER in system + "".join(
            m.get("content", "") for m in messages) else "no attachment")
        # Si parece el extractor, devolvemos JSON de metadata plausible.
        if "Return the updated metadata as JSON" in (messages[-1].get("content", "") if messages else ""):
            text = '{"project_name": null, "assumed_team_size": null, ' \
                   '"mentioned_technologies": [], "agreed_scope": null}'
        latency = 50 + chars / 1000.0
        return LLMResult(
            text=text, latency_ms=latency, tokens_in=tokens_in, tokens_out=tokens_out,
            cost_usd=cost_usd("claude-haiku-4-5", tokens_in, tokens_out),
            model="fake-haiku", provider="fake",
        )

    ss.complete_observed = fake
    me.complete_observed = fake


def _make_client(http: str | None, fake: bool) -> httpx.AsyncClient:
    if http:
        return httpx.AsyncClient(base_url=http)
    if fake:
        _install_fake_llm()
    from app.main import app

    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def main_async(args) -> None:
    scenario_names = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    attachment_sizes = [int(s) for s in args.attachment_sizes.split(",") if s.strip() != ""]
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    client = _make_client(args.http, args.fake)
    try:
        rows = await run(
            client, scenario_names, attachment_sizes, args.repeats, args.max_turns, phases
        )
    finally:
        await client.aclose()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} filas -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress test del CAG")
    parser.add_argument("--http", default=None, help="URL del servidor (si se omite, in-process)")
    parser.add_argument("--scenarios", default="growing,pivot,contradiction")
    parser.add_argument("--attachment-sizes", default="0,5,20,50,100")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--phases", default="multiturn,attachments")
    parser.add_argument("--output", default="evals/stress/results.csv")
    parser.add_argument("--fake", action="store_true", help="LLM stub determinista (in-process)")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
