"""Base tester helpers for wrapping external core binaries.

Helpers here are intentionally small and mostly used by tester modules.
"""

from __future__ import annotations

import asyncio
import subprocess
import json
from typing import Dict, Any

from .network_metrics import Metrics, measure_throughput


class TesterBase:
    def __init__(self, core_binary: str) -> None:
        self.core = core_binary

    async def _start_core(self, config_json: Dict[str, Any]) -> subprocess.Popen:
        # Write config to temp file and start core
        import tempfile
        import os

        fd, path = tempfile.mkstemp(prefix="core_config_", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config_json, f)

        proc = subprocess.Popen(
            [self.core, "-c", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        await asyncio.sleep(0.2)
        return proc

    async def _stop_core(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    async def test_config(self, config: Dict[str, Any]) -> Metrics:
        # Start core and run a small probe
        proc = await self._start_core(config)
        try:
            m = await measure_throughput("http://127.0.0.1:1080")
        finally:
            await self._stop_core(proc)
        return m
