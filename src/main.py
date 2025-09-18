"""Small runnable entrypoint for the package.

This file provides a minimal async runner used by developers and CI.
"""

from __future__ import annotations

import asyncio
from typing import List

from .fetcher import SubscriptionFetcher
from .filter import filter_and_rank
from .config import Config
from .utils import safe_write


async def run_once() -> None:
    """Fetch subscriptions, apply (placeholder) metrics and filter them.

    The current runner is intentionally minimal for smoke runs.
    """
    sources: List[str] = []
    fetcher = SubscriptionFetcher(sources)
    raw = await fetcher.fetch_all()

    # placeholder metrics (unknown / failed)
    metrics_map = {r: None for r in raw}
    filtered = filter_and_rank(raw, metrics_map)
    safe_write(Config.OUTPUT_PLAIN_PATH, "\n".join(filtered))


def main() -> None:
    asyncio.run(run_once())


if __name__ == "__main__":
    main()
