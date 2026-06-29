"""Contrato común de las métricas: `MetricResult`.

Toda métrica devuelve un `MetricResult` con `name`, `score` (float), `passed`
(bool) y `details` (str legible). Determinismo > sofisticación: nada de
embeddings ni LLM-as-judge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetricResult:
    name: str
    score: float
    passed: bool
    details: str = ""
