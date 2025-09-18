"""Filtering and ranking utilities for proxy configurations.

This module provides functions to filter a list of raw proxy configurations based on
network metrics, score them, and then rank them.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .config import Config
from .network_metrics import Metrics, MetricsAnalyzer


def_strip_remark(config_line: str) -> str:
    """Removes the remark part (text after '#') from a config line."""
    return config_line.split("#")[0].strip()


def_create_remark(metrics: Metrics) -> str:
    """Creates a standardized remark string from network metrics."""
    # Ensure values are reasonable for display
    lat = int(metrics.latency_ms) if metrics.latency_ms is not None else "N/A"
    thr_kbps = int(metrics.throughput_kbps) if metrics.throughput_kbps is not None else "N/A"
    loss = f"{metrics.packet_loss:.1f}%" if metrics.packet_loss is not None else "N/A"
    
    # More compact and informative remark
    return f"Speed:{thr_kbps}KB/s-Latency:{lat}ms-Loss:{loss}"


def is_supported_protocol(config_line: str) -> bool:
    """Checks if the protocol of the config line is in the supported list."""
    protocol_match = re.match(r"^(\w+)://", config_line)
    if not protocol_match:
        return False
    return protocol_match.group(1).lower() in Config.SUPPORTED_PROTOCOLS


def filter_and_rank(
    raw_configs: List[str],
    metrics_map: Dict[str, Optional[Metrics]],
    min_throughput_kbps: int = Config.MIN_THROUGHPUT_KBPS,
    max_latency_ms: int = Config.MAX_LATENCY_MS,
) -> List[str]:
    """Filters, scores, and ranks nodes based on metrics and returns a sorted list of configs with new remarks."""
    
    scored_nodes = []
    for config in raw_configs:
        # 1. Pre-filter by protocol
        if not is_supported_protocol(config):
            continue

        metrics = metrics_map.get(config)

        # 2. Filter by success and basic thresholds
        if not metrics or not metrics.success:
            continue
        if metrics.latency_ms is None or metrics.latency_ms > max_latency_ms:
            continue
        if metrics.throughput_kbps is None or metrics.throughput_kbps < min_throughput_kbps:
            continue

        # 3. Score the node
        score = MetricsAnalyzer.score(metrics)
        if score <= 0:
            continue

        # 4. Prepare for ranking
        base_config = _strip_remark(config)
        remark = _create_remark(metrics)
        final_config = f"{base_config}#{remark}"
        scored_nodes.append((score, final_config))

    # 5. Sort by score in descending order (higher is better)
    scored_nodes.sort(reverse=True, key=lambda t: t[0])

    # Return only the config string
    return [t[1] for t in scored_nodes]
