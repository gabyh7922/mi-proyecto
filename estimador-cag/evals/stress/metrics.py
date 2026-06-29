"""Bloque 4 — Tres métricas nuevas para el stress test.

Viven aquí (y no en ``evals/metrics.py``) porque dependen del shape de
``turn_observed`` y del snapshot de sesión, no de un ``EstimationResult`` como
las métricas golden. Reusan el mismo contrato ``MetricResult``.

Determinismo > sofisticación: presupuestos = comparación numérica; drift = match
exacto case-insensitive (substring) sobre los campos del snapshot. Nada de
embeddings ni LLM-as-judge.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from evals.metrics import MetricResult


class LatencyBudgetMetric:
    """1.0 si latency_ms <= budget_ms; 0.0 si no.

    El SLA del cliente deja de ser una observación a posteriori y se convierte en
    un test (un presupuesto es un contrato de diseño).
    """

    def __init__(self, budget_ms: int):
        self.budget_ms = budget_ms

    def evaluate(self, observation: dict) -> MetricResult:
        latency = observation.get("latency_ms")
        if latency is None:
            return MetricResult("latency_budget", 0.0, False, "sin latency_ms en la observación")
        passed = latency <= self.budget_ms
        return MetricResult(
            "latency_budget",
            1.0 if passed else 0.0,
            passed,
            f"{latency:.0f}ms vs budget {self.budget_ms}ms",
        )


class CostBudgetMetric:
    """1.0 si cost_usd <= budget_usd; 0.0 si no."""

    def __init__(self, budget_usd: float):
        self.budget_usd = budget_usd

    def evaluate(self, observation: dict) -> MetricResult:
        cost = observation.get("cost_usd")
        if cost is None:
            return MetricResult("cost_budget", 0.0, False, "sin cost_usd en la observación")
        passed = cost <= self.budget_usd
        return MetricResult(
            "cost_budget",
            1.0 if passed else 0.0,
            passed,
            f"${cost:.6f} vs budget ${self.budget_usd:.6f}",
        )


class MemoryDriftMetric:
    """1.0 si el fact declarado en el turno k aparece en el summary, anchors o
    ProjectMetadata del turno N (con N > k); 0.0 si no.

    Match exacto (case-insensitive, substring) contra los campos del snapshot.
    """

    def __init__(self, fact: str, where: Iterable[str] = ("summary", "anchors", "metadata")):
        self.fact = fact
        self.where = tuple(where)

    def evaluate(self, snapshot: dict) -> MetricResult:
        haystack = _haystack(snapshot, self.where)
        found = self.fact.lower() in haystack
        return MetricResult(
            "memory_drift",
            1.0 if found else 0.0,
            found,
            f"fact {self.fact!r} {'presente' if found else 'PERDIDO'} en {list(self.where)}",
        )


def _haystack(snapshot: dict, where: tuple[str, ...]) -> str:
    """Concatena en minúsculas el texto de los campos pedidos del snapshot."""
    parts: list[str] = []
    for field in where:
        value = snapshot.get(field)
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
        else:
            # dict (metadata) o list (anchors) -> JSON plano
            parts.append(json.dumps(value, default=str, ensure_ascii=False))
    return " ".join(parts).lower()
