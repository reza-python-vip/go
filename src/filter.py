"""Filtering and ranking utilities.

Given raw node lines and a metrics mapping, produce a ranked list of nodes
with a simple remark appended.
"""

from __future__ import annotations

import json
from typing import List, Dict

from .network_metrics import MetricsAnalyzer, Metrics
from .config import Config
from .utils import safe_write


def annotate_remark(metrics: Metrics) -> str:
    lat = int(metrics.latency_ms or 0)
    thr_kbps = int(metrics.throughput_kbps or 0)
    loss = metrics.packet_loss or 0
    return f"[AutoTest] | {lat}ms | thr {thr_kbps}kbps | loss {loss}%"


def filter_and_rank(raw_configs: List[str], metrics_map: Dict[str, Metrics]) -> List[str]:
    scored = []
    for cfg in raw_configs:
        m = metrics_map.get(cfg)
        score = MetricsAnalyzer.score(m) if m else 0.0
        if score <= 0:
            continue
        remark = annotate_remark(m)
        scored.append((score, cfg, remark))

    scored.sort(reverse=True, key=lambda t: t[0])
    lines = [f"{t[1]}#{t[2]}" for t in scored]

    safe_write(Config.OUTPUT_PLAIN_PATH, "\n".join(lines))
    # write a base64-style subscription as plain text to the base64 path
    safe_write(Config.OUTPUT_BASE64_PATH, json.dumps("\n".join(lines)))
    return lines

