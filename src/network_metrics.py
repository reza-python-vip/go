"""Compatibility shim: provide `Metrics` type expected by older modules.

Some modules in the codebase import `Metrics` from `src.network_metrics`.
The canonical dataclass is `NodeMetrics` in `src.models`. To avoid changing many
imports, expose `Metrics` as an alias to `NodeMetrics` here.
"""
from .models import NodeMetrics as Metrics

__all__ = ["Metrics"]
