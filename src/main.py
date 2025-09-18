"""The main entrypoint for the V2Ray/Xray configuration aggregator and tester.

This module orchestrates the fetching, testing, filtering, and saving of proxy configurations.
It is designed to be run as the main script and leverages asyncio for concurrent network operations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from .config import Config
from .fetcher import SubscriptionFetcher
from .filter import filter_and_rank
from .network_metrics import Metrics
from .reporter import generate_subscription_links
from .tester_base import NodeTester
from .xray_tester import XrayTester
from .utils import safe_write

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def test_all_nodes(tester: NodeTester, configs: List[str]) -> Dict[str, Metrics | None]:
    """Tests a list of configurations concurrently and returns their metrics."""
    tasks = [tester.test_node(c) for c in configs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    metrics_map = {}
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            logging.error(f"Error testing node {configs[i][:30]}...: {res}")
            metrics_map[configs[i]] = None
        else:
            metrics_map[configs[i]] = res
            if res and res.success:
                logging.info(f"Success: {configs[i][:60]}... -> Latency: {res.latency_ms}ms, Throughput: {res.throughput_kbps} KB/s")
            else:
                logging.warning(f"Failed or slow: {configs[i][:60]}...")
    
    return metrics_map


async def run_once() -> None:
    """Fetches subscriptions, tests them, filters them, and saves the results."""
    logging.info("Starting the process...")

    # 1. Fetch configurations from all subscription sources
    sources = Config.get_subscription_sources()
    if not sources:
        logging.warning("No subscription sources found. Exiting.")
        return

    logging.info(f"Fetching from {len(sources)} subscription sources...")
    fetcher = SubscriptionFetcher(sources)
    raw_configs = await fetcher.fetch_all()
    logging.info(f"Fetched a total of {len(raw_configs)} configurations.")

    if not raw_configs:
        logging.info("No configurations fetched. Nothing to do.")
        return

    # 2. Test all fetched configurations to get network metrics
    logging.info("Initializing the tester...")
    tester = XrayTester(Config.XRAY_BINARY, Config.CACHE_DIR, Config.HTTP_TIMEOUT)

    logging.info(f"Testing {len(raw_configs)} nodes with concurrency limit {Config.MAX_CONCURRENT_TESTS}...")
    semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TESTS)
    async with tester:
        async with semaphore:
            metrics_map = await test_all_nodes(tester, raw_configs)

    successful_tests = sum(1 for m in metrics_map.values() if m and m.success)
    logging.info(f"Testing complete. {successful_tests} nodes passed the tests.")

    # 3. Filter and rank the configurations based on metrics
    logging.info("Filtering and ranking nodes based on performance...")
    filtered_configs = filter_and_rank(raw_configs, metrics_map)
    logging.info(f"Filtered down to {len(filtered_configs)} high-quality nodes.")

    if not filtered_configs:
        logging.warning("No nodes passed the filtering criteria. Output files will be empty.")

    # 4. Write the results to output files
    logging.info("Writing filtered nodes to output files...")
    plain_text_output = "\n".join(filtered_configs)
    safe_write(Config.OUTPUT_PLAIN_PATH, plain_text_output)
    logging.info(f"Wrote {len(filtered_configs)} nodes to {Config.OUTPUT_PLAIN_PATH}")

    # 5. Generate and save the base64-encoded subscription file
    sub_link_plain, sub_link_b64 = generate_subscription_links(filtered_configs)
    safe_write(Config.OUTPUT_BASE64_PATH, sub_link_b64)
    logging.info(f"Wrote base64 subscription to {Config.OUTPUT_BASE64_PATH}")
    
    logging.info("Process finished successfully!")
    print(f"\nSubscription link (plaintext): {sub_link_plain}")
    print(f"Subscription link (base64): {sub_link_b64}")


def main() -> None:
    """The synchronous entrypoint for the asyncio runner."""
    try:
        asyncio.run(run_once())
    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
    except Exception as e:
        logging.critical(f"An unhandled error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main()
