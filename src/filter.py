"""Filtering and ranking utilities for proxy configurations.

This module provides functions to filter a list of raw proxy configurations based on
network metrics, score them, and then rank them. It has been refactored for
clarity and modularity.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple

from .config import Config
from .network_metrics import Metrics, MetricsAnalyzer
from .utils import get_node_id


def _create_remark(metrics: Metrics, score: float) -> str:
    """Creates a standardized remark string from network metrics and score."""
    lat = int(metrics.latency_ms) if metrics.latency_ms is not None else "N/A"
    jit = int(metrics.jitter_ms) if metrics.jitter_ms is not None else "N/A"
    thr_kbps = int(metrics.throughput_kbps) if metrics.throughput_kbps is not None else "N/A"
    
    # Convert throughput to MB/s for readability if it's large
    if isinstance(thr_kbps, int) and thr_kbps >= 1000:
        thr_display = f"{thr_kbps / 1024:.2f}MB/s"
    else:
        thr_display = f"{thr_kbps}KB/s"

    return f"[S:{score:.1f}]-Speed:{thr_display}-Latency:{lat}ms-Jitter:{jit}ms"

def _is_node_eligible(config: str, metrics: Optional[Metrics]) -> bool:
    """Determines if a node is eligible for ranking based on preliminary checks."""
    protocol_match = re.match(r"^(\w+)://", config)
    if not protocol_match or protocol_match.group(1).lower() not in Config.SUPPORTED_PROTOCOLS:
        logging.debug(f"Node {get_node_id(config)} skipped: Unsupported protocol.")
        return False

    if not metrics or not metrics.success:
        logging.debug(f"Node {get_node_id(config)} skipped: Failed test or no metrics.")
        return False

    if metrics.latency_ms is None or metrics.latency_ms > Config.MAX_LATENCY_MS:
        logging.debug(f"Node {get_node_id(config)} skipped: Latency ({metrics.latency_ms}ms) > {Config.MAX_LATENCY_MS}ms.")
        return False

    if metrics.throughput_kbps is None or metrics.throughput_kbps < Config.MIN_THROUGHPUT_KBPS:
        logging.debug(f"Node {get_node_id(config)} skipped: Throughput ({metrics.throughput_kbps}KB/s) < {Config.MIN_THROUGHPUT_KBPS}KB/s.")
        return False

    return True

def _score_and_prepare_nodes(
    eligible_configs: List[str],
    metrics_map: Dict[str, Optional[Metrics]],
) -> List[Tuple[float, str]]:
    """Scores the eligible nodes and prepares them for ranking."""
    scored_nodes = []
    for config in eligible_configs:
        metrics = metrics_map.get(config)
        if not metrics: continue

        score = MetricsAnalyzer.score(metrics)
        if score <= 1:  # Filter out nodes with a score of 1 or less, which is effectively a fail
            logging.debug(f"Node {get_node_id(config)} filtered out: Low score ({score:.2f}).")
            continue

        base_config = config.split("#")[0].strip()
        remark = _create_remark(metrics, score)
        final_config = f"{base_config}#{remark}"
        scored_nodes.append((score, final_config))
    
    return scored_nodes

def filter_and_rank(
    raw_configs: List[str],
    metrics_map: Dict[str, Optional[Metrics]],
) -> List[str]:
    """Filters, scores, and ranks nodes based on metrics.

    This function is now a high-level orchestrator that uses helper functions
    for eligibility checking, scoring, and sorting.
    """
    
    # 1. First pass: Filter out nodes that are not even eligible for ranking.
    logging.info("Starting initial filtering of nodes...")
    eligible_configs = [config for config in raw_configs if _is_node_eligible(config, metrics_map.get(config))]
    logging.info(f"{len(eligible_configs)} nodes are eligible for scoring and ranking.")

    # 2. Score the eligible nodes and create a new config with a remark.
    logging.info("Scoring and preparing remarks for eligible nodes...")
    scored_nodes = _score_and_prepare_nodes(eligible_configs, metrics_map)

    # 3. Sort by score in descending order (higher is better).
    logging.info("Ranking nodes by their final score...")
    scored_nodes.sort(reverse=True, key=lambda t: t[0])

    # Return only the config string from the sorted tuples.
    return [t[1] for t in scored_nodes]
