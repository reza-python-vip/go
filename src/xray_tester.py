"""Lightweight wrapper around the xray core binary for testing."""

from __future__ import annotations

from .tester_base import TesterBase


class XrayTester(TesterBase):
    """Tester for xray core."""

    def __init__(self) -> None:
        super().__init__(core_binary="xray")
