import pytest
from unittest.mock import MagicMock
from src.filter import _score_node, _create_remark, filter_and_rank
from src.models import Node, NodeMetrics
from src.config import Config


@pytest.fixture
def mock_config():
    """Provides a mock Config object for tests."""
    config = MagicMock(spec=Config)
    config.MAX_LATENCY_MS = 2000
    config.MIN_THROUGHPUT_KBPS = 100
    config.MIN_RELIABILITY = 0.8
    return config


def test_score_node(mock_config):
    # High score case
    high_perf_metrics = NodeMetrics(node_id="1", success=True, latency_ms=100, throughput_kbps=8000)
    score = _score_node(high_perf_metrics, mock_config)
    assert score > 80

    # Low score case
    low_perf_metrics = NodeMetrics(node_id="2", success=True, latency_ms=1800, throughput_kbps=200)
    score = _score_node(low_perf_metrics, mock_config)
    assert score > 0 and score < 50

    # Edge case: zero latency
    zero_latency_metrics = NodeMetrics(node_id="3", success=True, latency_ms=0, throughput_kbps=5000)
    score = _score_node(zero_latency_metrics, mock_config)
    assert score == 69.0


def test_create_remark():
    metrics = NodeMetrics(node_id="1", success=True, latency_ms=150, throughput_kbps=1200)
    remark = _create_remark(metrics, 85)
    assert remark == "[S:85] 1.17MB/s 150ms"

    metrics_kbps = NodeMetrics(node_id="2", success=True, latency_ms=200, throughput_kbps=500)
    remark_kbps = _create_remark(metrics_kbps, 60)
    assert remark_kbps == "[S:60] 500KB/s 200ms"


def test_filter_and_rank(mock_config):
    # Create nodes with configs that will generate different node_ids
    nodes = [
        Node(config="vmess://test-node-1"), # High score, reliable
        Node(config="vmess://test-node-2"), # Lower score, reliable
        Node(config="vmess://test-node-3"), # Failed test
        Node(config="vmess://test-node-4"), # High score, unreliable
    ]

    metrics = [
        NodeMetrics(node_id=nodes[0].node_id, success=True, latency_ms=100, throughput_kbps=5000),
        NodeMetrics(node_id=nodes[1].node_id, success=True, latency_ms=1500, throughput_kbps=500),
        NodeMetrics(node_id=nodes[2].node_id, success=False, latency_ms=0, throughput_kbps=0),
        NodeMetrics(node_id=nodes[3].node_id, success=True, latency_ms=200, throughput_kbps=6000),
    ]

    history = MagicMock()
    history.get_reliability.side_effect = lambda nid: 0.9 if nid in [nodes[0].node_id, nodes[1].node_id] else 0.5

    ranked_nodes = filter_and_rank(nodes, metrics, history, mock_config)

    assert len(ranked_nodes) == 2
    # Node 1 should be first as it has a higher score
    assert nodes[0].config in ranked_nodes[0].config
    assert nodes[1].config in ranked_nodes[1].config
    
    # Check if remarks are updated
    assert "[S:" in ranked_nodes[0].config