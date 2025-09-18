"""Utility helpers used across the project.

Small, well-scoped helpers: session creation, timestamp formatting,
file writing and a simple TCP probe.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger


def make_session(timeout: int = 10, proxy: Optional[str] = None) -> aiohttp.ClientSession:
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    connector = aiohttp.TCPConnector(ssl=False, limit=100)
    return aiohttp.ClientSession(timeout=timeout_obj, connector=connector)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def safe_write(path: str, data: str, mode: str = "w") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding="utf-8")


async def probe_tcp(host: str, port: int, timeout: int = 5) -> bool:
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False
