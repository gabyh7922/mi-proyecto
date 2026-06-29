"""Framework de evaluación del estimador.

`MetricResult` es el contrato común de todas las métricas. Las métricas del
stress test viven en `evals.stress.metrics` (dependen del shape de
`turn_observed`, no de un `EstimationResult`), pero comparten este resultado.
"""

from evals.metrics import MetricResult

__all__ = ["MetricResult"]
