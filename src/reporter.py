"""Generates subscription output formats and detailed reports.

This module handles the creation of subscription files and human-readable
reports from the results of a scan.
"""

from __future__ import annotations

import base64
import datetime
from typing import Dict, List, Optional, Tuple

from .network_metrics import Metrics

def get_report_string(
    filtered_configs: List[str],
    metrics_map: Dict[str, Optional[Metrics]],
    top_n: int = 10,
) -> str:
    """Generates a detailed, human-readable report of the scan results."""
    total_tested = len(metrics_map)
    successful_nodes_count = sum(1 for m in metrics_map.values() if m and m.success)
    success_rate = (successful_nodes_count / total_tested) * 100 if total_tested > 0 else 0

    report_lines = []
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report_lines.append("=" * 60)
    report_lines.append("      V2Ray Scanner Ultimate - Scan Report")
    report_lines.append("=" * 60)
    report_lines.append(f"Date: {now}")
    report_lines.append("-" * 60)
    report_lines.append(f"Total Nodes Tested:       {total_tested}")
    report_lines.append(f"Successful Connections:   {successful_nodes_count} ({success_rate:.1f}%)")
    report_lines.append(f"High-Quality Nodes Found: {len(filtered_configs)}")
    report_lines.append("-" * 60)

    if not filtered_configs:
        report_lines.append("\nNo high-quality nodes were found that meet the criteria.")
        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    hq_metrics_list = [(c, metrics_map.get(c)) for c in filtered_configs]
    hq_metrics_list = [(c, m) for c, m in hq_metrics_list if m]  # Remove None metrics

    latencies = [m.latency_ms for _, m in hq_metrics_list if m.latency_ms is not None]
    throughputs = [m.throughput_kbps for _, m in hq_metrics_list if m.throughput_kbps is not None]
    jitters = [m.jitter_ms for _, m in hq_metrics_list if m.jitter_ms is not None]

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    avg_throughput_kbps = sum(throughputs) / len(throughputs) if throughputs else 0
    avg_jitter = sum(jitters) / len(jitters) if jitters else 0

    report_lines.append("\n**Statistics for High-Quality Nodes:**")
    report_lines.append(f"- Average Latency:      {avg_latency:.2f} ms")
    report_lines.append(f"- Average Throughput:   {avg_throughput_kbps / 1024:.2f} MB/s")
    report_lines.append(f"- Average Jitter:       {avg_jitter:.2f} ms")

    report_lines.append(f"\n**Top {min(top_n, len(filtered_configs))} High-Quality Nodes (sorted by score):**")
    report_lines.append("-" * 60)
    for i, (config, metrics) in enumerate(hq_metrics_list[:top_n]):
        remark = config.split('#')[-1]
        report_lines.append(f"{i+1}. {remark}")
        report_lines.append(f"   - Latency: {metrics.latency_ms:.0f}ms | Jitter: {metrics.jitter_ms:.0f}ms | Reliability: {metrics.reliability * 100:.1f}%")
        report_lines.append(f"   - Node: {config.split('#')[0][:70]}...")

    report_lines.append("\n" + "=" * 60)
    return "\n".join(report_lines)

def generate_subscription_links(filtered_configs: List[str]) -> Tuple[str, str]:
    """Generates both plain-text and base64-encoded subscription content."""
    plain_text_sub = "\n".join(filtered_configs)
    if not filtered_configs:
        base64_sub = ""
    else:
        base64_sub = base64.b64encode(plain_text_sub.encode("utf-8")).decode("utf-8")
    
    return plain_text_sub, base64_sub
