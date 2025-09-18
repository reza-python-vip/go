"""Hiddify core tester wrapper."""

from __future__ import annotations

from .tester_base import TesterBase


class HiddifyTester(TesterBase):
    """Tester for hiddify core."""

    def __init__(self) -> None:
        super().__init__(core_binary="hiddify")
