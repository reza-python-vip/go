from __future__ import annotations

import datetime
from typing import List

from .models import Node, NodeMetrics

def generate_report(
    ranked_nodes: List[Node],
    all_metrics: List[NodeMetrics],
) -> str:
    """Generates a detailed, human-readable Markdown report of the scan results."""
    total_tested = len(all_metrics)
    successful_nodes_count = sum(1 for m in all_metrics if m.success)
    success_rate = (successful_nodes_count / total_tested) * 100 if total_tested > 0 else 0

    hq_node_ids = {n.node_id for n in ranked_nodes}
    hq_metrics = [m for m in all_metrics if m.node_id in hq_node_ids]

    if hq_metrics:
        avg_latency = sum(m.latency_ms for m in hq_metrics) / len(hq_metrics)
        avg_throughput_kbps = sum(m.throughput_kbps for m in hq_metrics) / len(hq_metrics)
        avg_throughput_mbps = avg_throughput_kbps / 1024
    else:
        avg_latency = 0
        avg_throughput_mbps = 0

    # --- Report Header ---
    report_lines = [
        "# 🚀 Proxy Scan Report",
        f"*Generated on: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'')}*",
        "",
        "## 📊 Summary",
        f"- **Total Nodes Tested:** {total_tested}",
        f"- **Successful Nodes:** {successful_nodes_count} ({success_rate:.2f}% success rate)",
        f"- **High-Quality Nodes Found:** {len(ranked_nodes)}",
        "",
        "## ✨ High-Quality Node Statistics",
        f"- **Average Latency:** {avg_latency:.2f} ms",
        f"- **Average Throughput:** {avg_throughput_mbps:.2f} MB/s",
        "",
        "## 🏆 Top Ranked Nodes",
        "| Rank | Configuration |",
        "|:----:|:--------------|"
    ]

    # --- Report Table ---
    for i, node in enumerate(ranked_nodes, 1):
        report_lines.append(f"| {i} | `{node.config}` |")
    
    return "\n".join(report_lines)
