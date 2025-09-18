"""Subscription fetcher utilities.

This module provides a class to fetch proxy configurations from a list of
subscription URLs, decode them if necessary, and return a clean list of configs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

import aiohttp

from .config import Config
from .utils import decode_base64_text

class SubscriptionFetcher:
    """Manages fetching and decoding of subscription sources with retry logic."""

    def __init__(self, sources: List[str]):
        self.sources = sources
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def _fetch_one_with_retry(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetches content from a single URL with retries and exponential backoff."""
        last_exception = None
        for attempt in range(Config.MAX_RETRIES + 1):
            try:
                self.logger.info(f"Fetching from source: {url} (Attempt {attempt + 1}/{Config.MAX_RETRIES + 1})")
                timeout = aiohttp.ClientTimeout(total=Config.DOWNLOAD_TIMEOUT)
                async with session.get(url, timeout=timeout, headers=self.headers) as response:
                    response.raise_for_status()  # Raises for 4xx/5xx statuses
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < Config.MAX_RETRIES:
                    delay = Config.RETRY_DELAY * (Config.BACKOFF_FACTOR ** attempt)
                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
            except Exception as e:
                last_exception = e
                self.logger.error(f"An unexpected error occurred while fetching {url}: {e}", exc_info=True)
                break

        self.logger.error(f"All {Config.MAX_RETRIES + 1} attempts to fetch {url} failed.")
        raise last_exception if last_exception else aiohttp.ClientError(f"Failed to fetch {url}")

    async def fetch_all(self) -> List[str]:
        """Fetches all subscription sources concurrently and returns a list of decoded config lines."""
        all_configs: List[str] = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_one_with_retry(session, url) for url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            source_url = self.sources[i]
            if isinstance(res, Exception):
                self.logger.error(f"Failed to fetch {source_url} after multiple retries: {res}")
                continue

            decoded_text = decode_base64_text(res)
            if decoded_text:
                self.logger.info(f"Successfully decoded base64 content from {source_url}")
                raw_text = decoded_text
            else:
                self.logger.info(f"Content from {source_url} is not base64 or decoding failed; treating as plain text.")
                raw_text = res

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if lines:
                all_configs.extend(lines)
                self.logger.info(f"Added {len(lines)} configs from {source_url}")

        if not all_configs:
            self.logger.warning("No configurations were successfully fetched from any source.")
            return []
            
        unique_configs = list(dict.fromkeys(all_configs))
        self.logger.info(f"Total unique configurations fetched: {len(unique_configs)}")
        
        return unique_configs
