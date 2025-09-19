from __future__ import annotations

import logging
from typing import List, Dict

from .config import Config
from .history import HistoryManager
from .models import Node, NodeMetrics

logger = logging.getLogger(__name__)

def _score_node(metrics: NodeMetrics, config: Config) -> float:
    """Calculates a score for a node based on latency and throughput."""
    latency_score = max(0, 1 - (metrics.latency_ms / config.MAX_LATENCY_MS))
    throughput_cap = 10 * 1024  # Cap throughput at 10 MB/s for scoring
    throughput_score = min(1, metrics.throughput_kbps / throughput_cap)
    return round((latency_score * 0.4) + (throughput_score * 0.6), 2) * 100

def _create_remark(metrics: NodeMetrics, score: float) -> str:
    """Creates a standardized remark, e.g., [S:85] 1.2MB/s 150ms."""
    thr_mbps = metrics.throughput_kbps / 1024
    thr_display = f"{thr_mbps:.2f}MB/s" if thr_mbps >= 1 else f"{int(metrics.throughput_kbps)}KB/s"
    return f"[S:{int(score)}] {thr_display} {int(metrics.latency_ms)}ms"

def filter_and_rank(
    nodes: List[Node],
    metrics_list: List[NodeMetrics],
    history: HistoryManager,
    config: Config,
) -> List[Node]:
    """
    Filters, scores, and ranks nodes based on performance and reliability.

    Returns a sorted list of high-quality nodes with updated remarks.
    """
    node_map = {node.node_id: node for node in nodes}
    metrics_map = {m.node_id: m for m in metrics_list}

    logger.info(f"Starting filtering process with {len(nodes)} total nodes.")

    # 1. Initial success filter
    successful_ids = {m.node_id for m in metrics_list if m.success}
    logger.info(f"{len(successful_ids)} nodes passed the live test.")

    # 2. Historical reliability filter
    reliable_ids = {nid for nid in successful_ids if history.get_reliability(nid) >= config.MIN_RELIABILITY}
    logger.info(f"{len(reliable_ids)} nodes meet the reliability threshold ({config.MIN_RELIABILITY:%}).")

    # 3. Performance filter
    hq_ids = {
        nid for nid in reliable_ids
        if (metrics_map[nid].latency_ms < config.MAX_LATENCY_MS and
            metrics_map[nid].throughput_kbps > config.MIN_THROUGHPUT_KBPS)
    }
    logger.info(f"{len(hq_ids)} nodes meet performance criteria (Latency < {config.MAX_LATENCY_MS}ms, Speed > {config.MIN_THROUGHPUT_KBPS}KB/s)." )

    # 4. Score and Rank
    scored_nodes = []
    for node_id in hq_ids:
        score = _score_node(metrics_map[node_id], config)
        scored_nodes.append((score, node_id))
    
    scored_nodes.sort(key=lambda x: x[0], reverse=True)

    # 5. Finalize and update remarks
    final_nodes = []
    for score, node_id in scored_nodes:
        base_config = node_map[node_id].config.split("#")[0]
        remark = _create_remark(metrics_map[node_id], score)
        final_nodes.append(Node(config=f"{base_config}#{remark}"))

    logger.info(f"Returning {len(final_nodes)} high-quality, ranked nodes.")
    return final_nodes
