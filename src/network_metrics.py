"""Data structures and analysis for network performance metrics.

This module defines the `Metrics` dataclass to hold performance data and a
`MetricsAnalyzer` class with a static method to score the quality of a proxy node
based on its metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Metrics:
    """Holds the network performance metrics for a single proxy node."""
    success: bool
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss: Optional[float] = None
    throughput_kbps: Optional[float] = None


class MetricsAnalyzer:
    """Provides static methods for analyzing and scoring network metrics."""

    # Define weights for each metric component in the score calculation
    LATENCY_WEIGHT = 0.40
    THROUGHPUT_WEIGHT = 0.50
    PACKET_LOSS_WEIGHT = 0.10

    # Define ideal and unacceptable values for normalization
    IDEAL_LATENCY_MS = 50
    MAX_ACCEPTABLE_LATENCY_MS = 1500
    
    IDEAL_THROUGHPUT_KBPS = 10000  # 10 MB/s
    MIN_ACCEPTABLE_THROUGHPUT_KBPS = 100

    IDEAL_PACKET_LOSS = 0
    MAX_ACCEPTABLE_PACKET_LOSS = 5 # 5%

    @staticmethod
    def _normalize(value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
        """Normalizes a value to a 0-1 scale. If reverse is True, lower is better."""
        if reverse:
            value, min_val, max_val = max_val - value, max_val - max_val, max_val - min_val
        
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized)) # Clamp between 0 and 1

    @staticmethod
    def score(metrics: Optional[Metrics]) -> float:
        """Calculates a quality score (0.0 to 100.0) for a node based on its metrics.

        A score of 0 indicates a failed or unusable node.
        Higher scores indicate better performance.
        """
        if not metrics or not metrics.success:
            return 0.0

        # Ensure required metrics are present
        if metrics.latency_ms is None or metrics.throughput_kbps is None:
            return 0.0

        # --- Latency Score ---
        # Lower latency is better (reverse normalization)
        latency_score = MetricsAnalyzer._normalize(
            metrics.latency_ms,
            MetricsAnalyzer.IDEAL_LATENCY_MS,
            MetricsAnalyzer.MAX_ACCEPTABLE_LATENCY_MS,
            reverse=True
        )

        # --- Throughput Score ---
        # Higher throughput is better
        throughput_score = MetricsAnalyzer._normalize(
            metrics.throughput_kbps,
            MetricsAnalyzer.MIN_ACCEPTABLE_THROUGHPUT_KBPS,
            MetricsAnalyzer.IDEAL_THROUGHPUT_KBPS
        )

        # --- Packet Loss Score ---
        packet_loss = metrics.packet_loss if metrics.packet_loss is not None else 0
        # Lower packet loss is better (reverse normalization)
        loss_score = MetricsAnalyzer._normalize(
            packet_loss,
            MetricsAnalyzer.IDEAL_PACKET_LOSS,
            MetricsAnalyzer.MAX_ACCEPTABLE_PACKET_LOSS,
            reverse=True
        )
        
        # --- Final Weighted Score ---
        final_score = (
            latency_score * MetricsAnalyzer.LATENCY_WEIGHT +
            throughput_score * MetricsAnalyzer.THROUGHPUT_WEIGHT +
            loss_score * MetricsAnalyzer.PACKET_LOSS_WEIGHT
        )

        # Return score as a percentage
        return final_score * 100
