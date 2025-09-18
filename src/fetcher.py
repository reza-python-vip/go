"""Subscription fetcher utilities.

Small helper that downloads subscription blobs (optionally base64) and
extracts non-empty lines.
"""

from __future__ import annotations

import base64
from typing import List

import aiohttp

from .config import Config
from .utils import safe_write


class SubscriptionFetcher:
    def __init__(self, sources: List[str]):
        self.sources = sources

    async def _fetch_one(self, session: aiohttp.ClientSession, url: str) -> str:
        async with session.get(url, timeout=Config.DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            return await r.text()

    async def fetch_all(self) -> List[str]:
        out: List[str] = []
        async with aiohttp.ClientSession() as s:
            tasks = [self._fetch_one(s, u) for u in self.sources]
            results = await __import__('asyncio').gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                continue

            # attempt to decode base64; fall back to raw text
            try:
                raw = base64.b64decode(r).decode('utf-8')
            except Exception:
                raw = r

            out.extend(ln.strip() for ln in raw.splitlines() if ln.strip())

        safe_write(Config.RAW_CONFIGS_PATH, "\n".join(out))
        return out
