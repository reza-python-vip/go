"""Type definitions for the project."""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict, Union

from pydantic import BaseModel

class ProxyProtocolConfig(TypedDict):
    """Configuration for a proxy protocol."""
    name: str
    port_range: tuple[int, int]
    enabled: bool

class NodeConfig(BaseModel):
    """Configuration for a proxy node."""
    node_id: str
    config_str: str
    protocol: str
    enabled: bool = True
    last_success: Optional[float] = None
    success_rate: float = 0.0

class TestResult(TypedDict):
    """Result of a node test."""
    success: bool
    latency_ms: float
    throughput_kbps: float
    error: Optional[str]

class TestMetrics(BaseModel):
    """Metrics from node testing."""
    total_nodes: int
    successful_nodes: int
    average_latency: float
    average_throughput: float
    test_duration: float

ConfigType = Dict[str, Union[str, int, bool, ProxyProtocolConfig]]