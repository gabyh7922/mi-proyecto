"""Tests de las métricas del stress test (Bloque 4).

Una métrica que pasa, una que falla y un dato límite, por cada métrica.
Determinismo total: sin LLM ni red.
"""

from evals.stress.metrics import CostBudgetMetric, LatencyBudgetMetric, MemoryDriftMetric


# --- LatencyBudgetMetric ---
def test_latency_budget_pass():
    r = LatencyBudgetMetric(budget_ms=4000).evaluate({"latency_ms": 1200})
    assert r.passed and r.score == 1.0


def test_latency_budget_fail():
    r = LatencyBudgetMetric(budget_ms=4000).evaluate({"latency_ms": 9000})
    assert not r.passed and r.score == 0.0


def test_latency_budget_edge_equal():
    # Exactamente en el presupuesto -> pasa (<=).
    r = LatencyBudgetMetric(budget_ms=4000).evaluate({"latency_ms": 4000})
    assert r.passed


def test_latency_budget_missing_field():
    r = LatencyBudgetMetric(budget_ms=4000).evaluate({})
    assert not r.passed


# --- CostBudgetMetric ---
def test_cost_budget_pass():
    r = CostBudgetMetric(budget_usd=0.01).evaluate({"cost_usd": 0.002})
    assert r.passed and r.score == 1.0


def test_cost_budget_fail():
    r = CostBudgetMetric(budget_usd=0.01).evaluate({"cost_usd": 0.05})
    assert not r.passed


def test_cost_budget_edge_zero():
    # Coste cero (dato límite) -> pasa.
    r = CostBudgetMetric(budget_usd=0.01).evaluate({"cost_usd": 0.0})
    assert r.passed


# --- MemoryDriftMetric ---
def test_memory_drift_found_in_metadata():
    snap = {"summary": "", "anchors": [], "metadata": {"project_name": "Nimbus"}}
    r = MemoryDriftMetric("Nimbus").evaluate(snap)
    assert r.passed and r.score == 1.0


def test_memory_drift_lost():
    snap = {"summary": "", "anchors": [], "metadata": {"project_name": "Atlas"}}
    r = MemoryDriftMetric("Nimbus").evaluate(snap)
    assert not r.passed and r.score == 0.0


def test_memory_drift_case_insensitive_in_list():
    # Dato límite: el fact está dentro de una lista y con otra capitalización.
    snap = {"metadata": {"mentioned_technologies": ["React Native", "Flutter"]}}
    r = MemoryDriftMetric("flutter").evaluate(snap)
    assert r.passed


def test_memory_drift_respects_where():
    # Si solo miramos 'summary' y el fact está en metadata -> no se encuentra.
    snap = {"summary": "nothing here", "metadata": {"project_name": "Nimbus"}}
    r = MemoryDriftMetric("Nimbus", where=["summary"]).evaluate(snap)
    assert not r.passed
