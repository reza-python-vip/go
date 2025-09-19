from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Union
from urllib.parse import urlparse

@dataclass(frozen=True)
class Node:
    """Represents a single proxy configuration, identified by its unique properties."""
    config: str
    node_id: str = field(init=False, hash=True)

    def __post_init__(self) -> None:
        """Generate a stable ID from the core components of the config URI."""
        base_config: str = self.config.split('#')[0].strip()
        parsed: urlparse.ParseResult = urlparse(base_config)
        
        # Use hostname and port for a stable ID
        if parsed.hostname and parsed.port:
            # Include path if it's significant for certain protocols
            if parsed.scheme in {'ws', 'grpc'} and parsed.path and parsed.path != '/':
                identifier: str = f"{parsed.hostname}:{parsed.port}:{parsed.path}"
            else:
                identifier: str = f"{parsed.hostname}:{parsed.port}"
        else:
            # Fallback for non-standard URIs
            identifier: str = base_config
            
        # Use a non-crypto hash for speed, as it's for identification not security
        hasher: hashlib._Hash = hashlib.sha256()
        hasher.update(identifier.encode('utf-8'))
        # We need to set the field on the object itself, despite it being frozen.
        # This is a standard pattern for initializing fields in frozen dataclasses.
        object.__setattr__(self, 'node_id', hasher.hexdigest())

@dataclass
class NodeMetrics:
    """Holds the performance metrics for a specific node test."""
    node_id: str
    success: bool
    latency_ms: float = 0.0
    throughput_kbps: float = 0.0
    error: Optional[str] = None  # Type of error if success is False

    def to_dict(self) -> dict[str, Union[str, bool, float, None]]:
        """Convert metrics to dictionary format.
        
        Returns:
            A dictionary containing the metrics data.
        """
        return {
            'node_id': self.node_id,
            'success': self.success,
            'latency_ms': self.latency_ms,
            'throughput_kbps': self.throughput_kbps,
            'error': self.error
        }
