"""Smoke test del runner del stress test con LLM fake (sin coste de API).

Ejercita el cableado end-to-end (crear sesión → estimar → leer snapshot →
evaluar métricas → escribir CSV) en modo in-process con el stub determinista,
para que un bug en la fontanería de `turn_observed`, el schema del CSV o las
llamadas a métricas salte en segundos sin gastar créditos de LLM.
"""

from __future__ import annotations

import csv
from pathlib import Path

import httpx
from httpx import ASGITransport

from evals.stress.run import CSV_COLUMNS, _install_fake_llm, run


def _fake_client() -> httpx.AsyncClient:
    _install_fake_llm()
    from app.main import app

    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_runner_end_to_end_writes_valid_csv(tmp_path: Path):
    client = _fake_client()
    try:
        rows = await run(
            client,
            scenario_names=["pivot"],
            attachment_sizes=[0, 5],
            repeats=1,
            max_turns=3,
            phases=["multiturn", "attachments"],
        )
    finally:
        await client.aclose()

    # multiturn: 3 turnos de pivot; attachments: 2 tamaños × 1 repeat = 2
    assert len(rows) == 3 + 2
    assert all(not r["error"] for r in rows), [r["error"] for r in rows if r["error"]]

    # Todas las filas tienen exactamente el schema esperado.
    for r in rows:
        assert set(r.keys()) == set(CSV_COLUMNS)

    # Las observaciones de turn_observed llegaron (tokens medidos por el fake).
    mt = [r for r in rows if r["phase"] == "multiturn"]
    assert all(int(r["tokens_in"]) > 0 for r in mt)
    assert mt[0]["turn_index"] == 1

    # El marcador del adjunto se detecta cuando hay adjunto (>0 KB).
    att = [r for r in rows if r["phase"] == "attachments" and int(r["attachment_kb"]) > 0]
    assert all(r["attachment_marker_recall"] == 1 for r in att)

    # El CSV se puede serializar y releer con el mismo schema.
    out = tmp_path / "results.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    reread = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(reread) == len(rows)


async def test_runner_multiturn_only_respects_max_turns(tmp_path: Path):
    client = _fake_client()
    try:
        rows = await run(
            client,
            scenario_names=["growing"],
            attachment_sizes=[0],
            repeats=1,
            max_turns=4,
            phases=["multiturn"],
        )
    finally:
        await client.aclose()

    assert len(rows) == 4
    assert [int(r["turn_index"]) for r in rows] == [1, 2, 3, 4]
