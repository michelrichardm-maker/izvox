"""Tests pour le pipeline."""

from src.config import FlowDirection
from src.pipeline import PipelineStats


def test_pipeline_stats_initial():
    stats = PipelineStats()
    assert stats.total_translations == 0
    assert stats.avg_latency_ms == 0.0
    assert stats.min_latency_ms == float("inf")
    assert stats.max_latency_ms == 0.0


def test_pipeline_stats_update():
    stats = PipelineStats()
    stats.update(100.0)
    stats.update(200.0)
    stats.update(50.0)
    assert stats.total_translations == 3
    assert stats.avg_latency_ms == pytest_approx(350.0 / 3)
    assert stats.min_latency_ms == 50.0
    assert stats.max_latency_ms == 200.0


def pytest_approx(value, rel=1e-3):
    """Wrapper minimal pour éviter d'importer pytest dans cette fonction utilitaire."""
    import pytest as _pytest
    return _pytest.approx(value, rel=rel)


def test_flow_direction_values():
    assert FlowDirection.OUTGOING.value == "outgoing"
    assert FlowDirection.INCOMING.value == "incoming"
