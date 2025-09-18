"""Subscription fetcher utilities.

This module provides a class to fetch proxy configurations from a list of
subscription URLs, decode them if necessary, and return a clean list of configs.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import List

import aiohttp

from .config import Config


class SubscriptionFetcher:
    """Manages fetching and decoding of subscription sources."""

    def __init__(self, sources: List[str]):
        self.sources = sources
        self.logger = logging.getLogger(self.__class__.__name__)
        # Use a common user-agent to avoid being blocked
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def _fetch_one(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetches and returns the content from a single URL."""
        self.logger.info(f"Fetching from source: {url}")
        async with session.get(url, timeout=Config.DOWNLOAD_TIMEOUT, headers=self.headers) as response:
            response.raise_for_status()  # Raises an exception for 4xx/5xx statuses
            return await response.text()

    async def fetch_all(self) -> List[str]:
        """Fetches all subscription sources concurrently and returns a list of decoded config lines."""
        all_configs: List[str] = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_one(session, url) for url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            source_url = self.sources[i]
            if isinstance(res, Exception):
                self.logger.error(f"Failed to fetch {source_url}: {res}")
                continue

            # The content might be base64 encoded, try to decode it.
            try:
                # Correctly handle padding issues with base64
                padding = len(res) % 4
                if padding != 0:
                    res += "=" * (4 - padding)
                decoded_content = base64.b64decode(res).decode("utf-8")
                self.logger.info(f"Successfully decoded base64 content from {source_url}")
                raw_text = decoded_content
            except (ValueError, TypeError, UnicodeDecodeError):
                # If decoding fails, assume it's plain text
                self.logger.info(f"Content from {source_url} is not base64, treating as plain text.")
                raw_text = res

            # Extend the list with non-empty, stripped lines
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if lines:
                all_configs.extend(lines)
                self.logger.info(f"Added {len(lines)} configs from {source_url}")

        # Remove duplicate configs to reduce redundant testing
        unique_configs = list(dict.fromkeys(all_configs))
        self.logger.info(f"Total unique configurations fetched: {len(unique_configs)}")
        
        return unique_configs
