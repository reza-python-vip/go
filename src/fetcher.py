from __future__ import annotations

import asyncio
import logging
from typing import List, Set

import aiohttp

from .utils import decode_base64_text

logger = logging.getLogger(__name__)


class SubscriptionFetcher:
    """Manages fetching and decoding of subscription sources."""

    def __init__(self, sources: List[str], timeout: float = 10.0):
        self.sources = sources
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def _fetch_one(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetches content from a single URL."""
        logger.debug(f"Fetching from source: {url}")
        try:
            async with session.get(
                url, timeout=self.timeout, headers=self.headers
            ) as response:
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            raise

    async def fetch_all(self) -> List[str]:
        """Fetches all subscriptions concurrently and processes the results."""
        all_configs: Set[str] = set()

        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_one(session, url) for url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            source_url = self.sources[i]
            if isinstance(result, Exception):
                logger.error(
                    f"Could not process subscription from {source_url}: {result}"
                )
                continue

            assert isinstance(result, str)
            logger.info(f"Successfully fetched content from {source_url}.")
            content = result
            decoded_text = decode_base64_text(content)
            raw_text = decoded_text if decoded_text else content

            lines = {line.strip() for line in raw_text.splitlines() if line.strip()}
            if lines:
                new_configs = lines - all_configs
                all_configs.update(new_configs)
                logger.info(
                    f"Added {len(new_configs)} new unique configs from {source_url}."
                )

        if not all_configs:
            logger.warning("No configurations were fetched from any source.")
            return []

        final_configs = list(all_configs)
        logger.info(f"Total unique configurations fetched: {len(final_configs)}")
        return final_configs


async def fetch_subscription_links(
    sources: list[str] | None = None, timeout: float = 10.0
) -> list[str]:
    """Convenience wrapper used by other modules to fetch subscription links.

    Args:
        sources: Optional list of sources. If None, callers should provide `config.SUBSCRIPTION_SOURCES`.
    """
    from .config import config

    sources = sources or config.SUBSCRIPTION_SOURCES
    fetcher = SubscriptionFetcher(sources, timeout=timeout)
    return await fetcher.fetch_all()
