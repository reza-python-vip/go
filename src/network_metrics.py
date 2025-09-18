"""Data structures and analysis for network performance metrics.

This module defines the `Metrics` dataclass to hold performance data and a
`MetricsAnalyzer` class with a static method to score the quality of a proxy node
based on its metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math

from .config import Config

@dataclass
class Metrics:
    """Holds the network performance metrics for a single proxy node."""
    success: bool
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss: Optional[float] = None
    throughput_kbps: Optional[float] = None
    reliability: Optional[float] = 1.0  # Default to 1.0 (100% reliable)


class MetricsAnalyzer:
    """Provides static methods for analyzing and scoring network metrics."""

    @staticmethod
    def _normalize_log(value: float, ideal: float) -> float:
        """Normalizes a value using a logarithmic scale where lower is better."""
        if value is None or value <= 0: return 0.0
        if ideal <= 0: ideal = 1
        return max(0.0, min(1.0, ideal / value))

    @staticmethod
    def _normalize_linear(value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
        """Normalizes a value to a 0-1 scale."""
        if reverse:
            if value >= max_val: return 0.0
            if value <= min_val: return 1.0
            return (max_val - value) / (max_val - min_val)
        else:
            if value <= min_val: return 0.0
            if value >= max_val: return 1.0
            return (value - min_val) / (max_val - min_val)
    
    @staticmethod
    def _get_latency_score(latency_ms: float) -> float:
        return MetricsAnalyzer._normalize_log(latency_ms, Config.IDEAL_LATENCY_MS)

    @staticmethod
    def _get_jitter_score(jitter_ms: float) -> float:
        return MetricsAnalyzer._normalize_linear(
            jitter_ms, Config.IDEAL_JITTER_MS, Config.MAX_JITTER_MS, reverse=True
        )

    @staticmethod
    def _get_throughput_score(throughput_kbps: float) -> float:
        return MetricsAnalyzer._normalize_linear(
            throughput_kbps, 0, Config.IDEAL_THROUGHPUT_KBPS
        )
    
    @staticmethod
    def _get_packet_loss_score(packet_loss: float) -> float:
        return MetricsAnalyzer._normalize_linear(
            packet_loss, Config.IDEAL_PACKET_LOSS, Config.MAX_PACKET_LOSS, reverse=True
        )

    @staticmethod
    def score(metrics: Optional[Metrics]) -> float:
        """Calculates a quality score (0.0 to 100.0) for a node."""
        if not metrics or not metrics.success or metrics.latency_ms is None or metrics.throughput_kbps is None or metrics.jitter_ms is None:
            return 0.0

        scores = {
            'latency': MetricsAnalyzer._get_latency_score(metrics.latency_ms),
            'jitter': MetricsAnalyzer._get_jitter_score(metrics.jitter_ms),
            'throughput': MetricsAnalyzer._get_throughput_score(metrics.throughput_kbps),
            'packet_loss': MetricsAnalyzer._get_packet_loss_score(metrics.packet_loss or 0)
        }

        weights = {
            'latency': Config.LATENCY_WEIGHT,
            'jitter': Config.JITTER_WEIGHT,
            'throughput': Config.THROUGHPUT_WEIGHT,
            'packet_loss': Config.PACKET_LOSS_WEIGHT
        }

        final_score = sum(scores[key] * weights[key] for key in scores)
        
        reliability_factor = metrics.reliability if metrics.reliability is not None else 1.0
        final_score *= (Config.RELIABILITY_WEIGHT * reliability_factor + (1-Config.RELIABILITY_WEIGHT))

        return max(0.0, final_score * 100)
