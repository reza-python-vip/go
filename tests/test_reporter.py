
import pytest
from src.reporter import generate_report
from src.models import Node, NodeMetrics


def test_generate_report():
    """Test that the report generation works correctly."""
    ranked_nodes = [
        Node(config="vmess://node1#remark1"),
        Node(config="vmess://node2#remark2"),
    ]
    # Manually set node_id for predictability in tests
    object.__setattr__(ranked_nodes[0], 'node_id', 'node1_id')
    object.__setattr__(ranked_nodes[1], 'node_id', 'node2_id')


    all_metrics = [
        NodeMetrics(node_id="node1_id", success=True, latency_ms=100, throughput_kbps=5000),
        NodeMetrics(node_id="node2_id", success=True, latency_ms=200, throughput_kbps=3000),
        NodeMetrics(node_id="node3_id", success=False, latency_ms=0, throughput_kbps=0),
    ]

    report = generate_report(ranked_nodes, all_metrics)

    # Check for key sections and stats in the report
    assert "# 🚀 Proxy Scan Report" in report
    assert "- **Total Nodes Tested:** 3" in report
    assert "- **Successful Nodes:** 2" in report
    assert "- **High-Quality Nodes Found:** 2" in report
    assert "- **Average Latency:** 150.00 ms" in report
    assert "- **Average Throughput:** 3.91 MB/s" in report # (5000+3000)/2/1024 = 3.90625
    assert "| 1 | `vmess://node1#remark1` |" in report
    assert "| 2 | `vmess://node2#remark2` |" in report
