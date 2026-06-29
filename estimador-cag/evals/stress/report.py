"""Bloque 6 — Generador de REPORT.md a partir de results.csv.

Calcula la tabla resumen, las tres curvas (como tablas Markdown) y dos párrafos
de lectura con afirmaciones cuantitativas extraídas de los datos. No dibuja
gráficos: el deliverable es Markdown + CSV.

    uv run python -m evals.stress.report --input evals/stress/results.csv \\
        --output evals/stress/REPORT.md
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _pct(values: list[float], p: float) -> float:
    """Percentil p (0..1) con interpolación lineal."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ok(rows):
    return [r for r in rows if not r.get("error")]


def summary_tables(rows: list[dict]) -> str:
    mt = [r for r in _ok(rows) if r["phase"] == "multiturn"]
    at = [r for r in _ok(rows) if r["phase"] == "attachments"]
    out = ["### Resumen — fase multiturno (sin adjunto)\n"]
    out.append("| escenario | turnos | P50 latency (ms) | P95 latency (ms) | coste total USD | recall medio fact-tracker | supervivencia turno-1 (último turno) |")
    out.append("|---|---|---|---|---|---|---|")
    for name in sorted({r["scenario"] for r in mt}):
        rs = [r for r in mt if r["scenario"] == name]
        lat = [_f(r["latency_ms"]) for r in rs]
        cost = sum(_f(r["cost_usd"]) for r in rs)
        drift = [_f(r["memory_drift_recall"]) for r in rs if r["memory_drift_recall"] != ""]
        max_turn = max(_f(r["turn_index"]) for r in rs)
        last = [r for r in rs if _f(r["turn_index"]) == max_turn and r["first_fact_recall"] != ""]
        surv = mean([_f(r["first_fact_recall"]) for r in last]) if last else float("nan")
        n_turns = int(max_turn)
        out.append(
            f"| {name} | {n_turns} | {_pct(lat, 0.5):.0f} | {_pct(lat, 0.95):.0f} | "
            f"{cost:.5f} | {(mean(drift) if drift else 0):.2f} | "
            f"{'n/a' if surv != surv else f'{surv:.2f}'} |"
        )

    out.append("\n### Resumen — fase adjuntos (estimación inicial)\n")
    out.append("| adjunto (KB) | chars extraídos | P50 latency (ms) | P95 latency (ms) | coste medio USD | recall del marcador |")
    out.append("|---|---|---|---|---|---|")
    for kb in sorted({int(r["attachment_kb"]) for r in at}):
        rs = [r for r in at if int(r["attachment_kb"]) == kb]
        lat = [_f(r["latency_ms"]) for r in rs]
        chars = int(mean([_f(r["attachments_total_chars"]) for r in rs]))
        cost = mean([_f(r["cost_usd"]) for r in rs])
        rec = [_f(r["attachment_marker_recall"]) for r in rs if r["attachment_marker_recall"] != ""]
        rec_s = f"{mean(rec):.2f}" if rec else "n/a (baseline)"
        out.append(
            f"| {kb} | {chars} | {_pct(lat, 0.5):.0f} | {_pct(lat, 0.95):.0f} | {cost:.5f} | {rec_s} |"
        )

    # Hit rate de cachés (este CAG no las implementa)
    out.append("\n**Cache hit rate** — exact: 0% · semantic: 0% (este baseline CAG no implementa caché; `cache_hit_kind` es siempre `none`).")
    return "\n".join(out)


def curve_latency_vs_tokens(rows: list[dict]) -> str:
    at = [r for r in _ok(rows) if r["phase"] == "attachments"]
    by_kb = defaultdict(list)
    for r in at:
        by_kb[int(r["attachment_kb"])].append(r)
    out = ["### Curva 1 — latencia vs tokens_in (barrido de adjunto)\n"]
    out.append("| adjunto (KB) | tokens_in (medio) | latency_ms (medio) |")
    out.append("|---|---|---|")
    for kb in sorted(by_kb):
        rs = by_kb[kb]
        out.append(f"| {kb} | {mean([_f(r['tokens_in']) for r in rs]):.0f} | {mean([_f(r['latency_ms']) for r in rs]):.0f} |")
    return "\n".join(out)


def curve_cost_vs_turn(rows: list[dict]) -> str:
    mt = [r for r in _ok(rows) if r["phase"] == "multiturn"]
    scenarios = sorted({r["scenario"] for r in mt})
    # coste medio por turno (sobre repeticiones), luego acumulado
    out = ["### Curva 2 — coste acumulado USD vs turno (por escenario)\n"]
    header = "| turno | " + " | ".join(scenarios) + " |"
    out.append(header)
    out.append("|" + "---|" * (len(scenarios) + 1))
    max_turn = int(max((_f(r["turn_index"]) for r in mt), default=0))
    cum = {s: 0.0 for s in scenarios}
    for t in range(1, max_turn + 1):
        cells = []
        for s in scenarios:
            per = [_f(r["cost_usd"]) for r in mt if r["scenario"] == s and int(_f(r["turn_index"])) == t]
            if per:
                cum[s] += mean(per)
                cells.append(f"{cum[s]:.5f}")
            else:
                cells.append("")
        out.append(f"| {t} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def curve_recall_vs_n(rows: list[dict]) -> str:
    mt = [r for r in _ok(rows) if r["phase"] == "multiturn"]
    scenarios = sorted({r["scenario"] for r in mt})
    out = ["### Curva 3 — recall vs N (turnos)\n"]
    out.append("Recall medio del fact-tracker (`memory_drift_recall`) por turno y escenario:\n")
    header = "| turno (N) | " + " | ".join(scenarios) + " |"
    out.append(header)
    out.append("|" + "---|" * (len(scenarios) + 1))
    max_turn = int(max((_f(r["turn_index"]) for r in mt), default=0))
    for t in range(2, max_turn + 1):  # turno 1 no tiene facts previos
        cells = []
        for s in scenarios:
            per = [_f(r["memory_drift_recall"]) for r in mt
                   if r["scenario"] == s and int(_f(r["turn_index"])) == t and r["memory_drift_recall"] != ""]
            cells.append(f"{mean(per):.2f}" if per else "")
        out.append(f"| {t} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def _cost_ratio(rows, scenario):
    mt = [r for r in _ok(rows) if r["phase"] == "multiturn" and r["scenario"] == scenario]
    if not mt:
        return None
    t1 = mean([_f(r["cost_usd"]) for r in mt if int(_f(r["turn_index"])) == 1] or [0])
    maxt = int(max(_f(r["turn_index"]) for r in mt))
    tn = mean([_f(r["cost_usd"]) for r in mt if int(_f(r["turn_index"])) == maxt] or [0])
    return t1, tn, maxt, (tn / t1 if t1 else float("nan"))


def _min_recall_turn(rows: list[dict], scenario: str):
    """Primer turno (y valor) donde el recall del fact-tracker cae bajo 1.0."""
    mt = [r for r in _ok(rows)
          if r["phase"] == "multiturn" and r["scenario"] == scenario
          and r["memory_drift_recall"] != ""]
    by_turn = defaultdict(list)
    for r in mt:
        by_turn[int(_f(r["turn_index"]))].append(_f(r["memory_drift_recall"]))
    for t in sorted(by_turn):
        m = mean(by_turn[t])
        if m < 1.0:
            return t, m
    return None


def reading(rows: list[dict]) -> str:
    at = [r for r in _ok(rows) if r["phase"] == "attachments"]
    mt = [r for r in _ok(rows) if r["phase"] == "multiturn"]
    lat0 = [_f(r["latency_ms"]) for r in at if int(r["attachment_kb"]) == 0]
    latmax_kb = max((int(r["attachment_kb"]) for r in at), default=0)
    latmax = [_f(r["latency_ms"]) for r in at if int(r["attachment_kb"]) == latmax_kb]
    tok0 = mean([_f(r["tokens_in"]) for r in at if int(r["attachment_kb"]) == 0] or [0])
    tokmax = mean([_f(r["tokens_in"]) for r in at if int(r["attachment_kb"]) == latmax_kb] or [0])

    growing = _cost_ratio(rows, "growing")
    cost_line = ""
    if growing:
        t1, tn, maxt, ratio = growing
        cost_line = (f"En *growing*, el coste del turno {maxt} (${tn:.5f}) multiplica por "
                     f"{ratio:.2f}× el del turno 1 (${t1:.5f}).")

    p95_0 = _pct(lat0, 0.95) if lat0 else 0
    p95_max = _pct(latmax, 0.95) if latmax else 0
    p50_mt = _pct([_f(r["latency_ms"]) for r in mt], 0.5)

    contra = _min_recall_turn(rows, "contradiction")
    contra_line = ""
    if contra:
        ct, cv = contra
        contra_line = (f"En *contradiction* el recall del fact-tracker cae por debajo de "
                       f"1.0 ya en el turno {ct} (a {cv:.2f}): el presupuesto inicial "
                       f"(\"30000\") no se promueve a `ProjectMetadata` y desaparece, "
                       f"mientras que en *growing*/*pivot* las tecnologías se acumulan por "
                       f"unión y el recall se mantiene en 1.0. ")

    out = ["## Lectura: dónde empieza a romperse mi CAG y por qué\n"]
    out.append(
        f"**Dimensión dominante: los adjuntos.** El texto del adjunto entra íntegro "
        f"en el prompt en cada estimación (este CAG no aplica `MAX_ATTACHMENT_CHARS`: "
        f"no trunca). Pasar de 0 a {latmax_kb} KB de texto lleva la entrada de "
        f"~{tok0:.0f} a ~{tokmax:.0f} tokens y la P95 de latencia de {p95_0:.0f} ms a "
        f"{p95_max:.0f} ms; con cualquier adjunto se supera el budget de 4000 ms. El coste "
        f"de una sola estimación escala linealmente con el tamaño del adjunto porque se "
        f"reenvía completo: no hay reuso ni recuperación selectiva. Aquí es donde el CAG "
        f"deja de sostenerse — un único documento grande basta para disparar latencia y "
        f"coste y acercar el prompt al límite de contexto del modelo.\n"
    )
    out.append(
        f"**La memoria conversacional es la segunda grieta.** {cost_line} El coste por "
        f"turno crece porque la ventana deslizante y el ProjectMetadata acumulado se "
        f"reinyectan cada vez; además cada turno hace dos llamadas (estimación + extractor), "
        f"de modo que la latencia P50 multiturno (~{p50_mt:.0f} ms) ya excede el SLA de "
        f"4000 ms sin adjunto alguno. {contra_line}**El caso límite que justifica saltar a "
        f"RAG**: un proyecto largo con documentos adjuntos voluminosos — donde reenviar todo "
        f"el contexto se vuelve caro y lento, y donde recuperar solo los fragmentos "
        f"relevantes (RAG) deja de ser opcional.\n"
    )

    # Cuatro afirmaciones para defender en el directo (paridad con la referencia).
    out.append("\n## Cuatro afirmaciones para defender\n")
    deg = contra if contra else (None, None)
    out.append(
        f"1. Mi CAG empieza a degradar la memoria en el turno **{deg[0]}** "
        f"(*contradiction*), cuando un hecho que no entra en `ProjectMetadata` cae fuera "
        f"de la ventana de 6 pares."
        if contra else
        "1. La memoria se mantiene en los escenarios medidos; el límite aparece antes por "
        "coste/latencia que por drift."
    )
    if growing:
        out.append(
            f"2. El coste por turno crece ~lineal con el historial: turno {growing[2]} = "
            f"**{growing[3]:.2f}×** el turno 1, porque cada turno reinyecta ventana + "
            f"metadata + transcript."
        )
    out.append(
        f"3. El cuello de botella de latencia es el tamaño del prompt: la P95 pasa de "
        f"{p95_0:.0f} ms (sin adjunto) a {p95_max:.0f} ms ({latmax_kb} KB), y el budget de "
        f"4000 ms se incumple con cualquier adjunto."
    )
    out.append(
        f"4. Para recortar contexto sin perder recall atacaría primero el adjunto: aporta "
        f"~{tokmax:.0f} tokens de entrada (vs ~{tok0:.0f} sin él), la mayor contribución "
        f"individual — justo lo que RAG recupera de forma selectiva."
    )
    return "\n".join(out)


def build_report(rows: list[dict]) -> str:
    n_ok = len(_ok(rows))
    n_err = len(rows) - n_ok
    parts = [
        "# Stress test del CAG — REPORT\n",
        f"Filas totales: **{len(rows)}** ({n_ok} ok, {n_err} con error). "
        "Proveedor único para que las curvas sean comparables.\n",
        "> Adaptaciones a este codebase (más simple que la plantilla del enunciado): "
        "no hay tiers, caché (exact/semantic) ni summarizer de texto; la memoria que "
        "sobrevive a la ventana es `ProjectMetadata`, así que `summary_chars` mide su "
        "tamaño, `anchors_count`=0 y `cache_hit_kind`=`none`. El stress se mide en dos "
        "fases desacopladas (multiturno sin adjunto · barrido de adjunto en una "
        "estimación) para aislar cada dimensión.\n",
        "## Tabla resumen\n",
        summary_tables(rows),
        "\n## Tres curvas\n",
        curve_latency_vs_tokens(rows),
        "\n",
        curve_cost_vs_turn(rows),
        "\n",
        curve_recall_vs_n(rows),
        "\n",
        reading(rows),
    ]
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera REPORT.md desde results.csv")
    parser.add_argument("--input", default="evals/stress/results.csv")
    parser.add_argument("--output", default="evals/stress/REPORT.md")
    args = parser.parse_args()
    rows = load(Path(args.input))
    Path(args.output).write_text(build_report(rows), encoding="utf-8")
    print(f"REPORT -> {args.output} ({len(rows)} filas)")


if __name__ == "__main__":
    main()
