"""The main entrypoint for the V2Ray/Xray configuration aggregator and tester.

This module orchestrates the fetching, testing, filtering, and saving of proxy configurations.
It is designed to be run as the main script and leverages asyncio for concurrent network operations.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Dict, List, Optional

from tqdm.asyncio import tqdm

from .config import Config
from .fetcher import SubscriptionFetcher
from .filter import filter_and_rank
from .history import HistoryManager
from .network_metrics import Metrics
from .reporter import generate_subscription_links, get_report_string
from .tester_base import NodeTester
from .xray_tester import XrayTester
from .utils import safe_write, get_node_id

# Configure logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def validate_config() -> bool:
    """Validates the application's configuration."""
    logging.info("Validating configuration...")
    if not Config.get_subscription_sources():
        logging.error("No subscription sources configured. Please check your config.")
        return False
    # Add more validation checks as needed
    logging.info("Configuration seems valid.")
    return True

async def test_all_nodes(
    tester: NodeTester, configs: List[str]
) -> Dict[str, Optional[Metrics]]:
    """Tests a list of configurations concurrently with a progress bar."""
    metrics_map: Dict[str, Optional[Metrics]] = {}
    
    # Wrap tasks with tqdm for a progress bar
    tasks = [tester.test_node(c) for c in configs]
    for i, task in enumerate(tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Testing Nodes")):
        config_url = configs[i] # This is not perfect but gives an idea
        try:
            res = await task
            metrics_map[config_url] = res
            if res and res.success:
                logging.debug(f"Success: {config_url[:60]}... -> {res.latency_ms}ms, {res.throughput_kbps} KB/s")
            else:
                logging.debug(f"Failed or slow: {config_url[:60]}...")
        except Exception as e:
            logging.error(f"Error testing node {config_url[:30]}...: {e}")
            metrics_map[config_url] = None
            
    return metrics_map

async def run_once() -> None:
    """Fetches subscriptions, tests them, filters, and saves the results."""
    logging.info("Starting the V2Ray Scanner Ultimate process...")

    history_manager = HistoryManager()
    history_manager.load_history()

    logging.info(f"Fetching from {len(Config.get_subscription_sources())} sources...")
    fetcher = SubscriptionFetcher(Config.get_subscription_sources())
    raw_configs = await fetcher.fetch_all()
    logging.info(f"Fetched {len(raw_configs)} unique configurations.")

    if not raw_configs:
        logging.warning("No configurations fetched. Nothing to do.")
        return

    tester = XrayTester(Config.XRAY_BINARY, Config.CACHE_DIR, Config.HTTP_TIMEOUT)
    async with tester:
        metrics_map = await test_all_nodes(tester, raw_configs)

    successful_tests = sum(1 for m in metrics_map.values() if m and m.success)
    logging.info(f"Testing complete. {successful_tests} nodes passed initial tests.")

    for config, metrics in metrics_map.items():
        node_id = get_node_id(config)
        reliability = history_manager.get_reliability(node_id)
        if metrics:
            metrics.reliability = reliability
        success = metrics.success if metrics else False
        history_manager.update_node_history(node_id, success)

    logging.info("Filtering and ranking nodes...")
    filtered_configs = filter_and_rank(raw_configs, metrics_map)
    logging.info(f"Filtered down to {len(filtered_configs)} high-quality nodes.")

    if not filtered_configs:
        logging.warning("No nodes passed filtering. Output files will be empty.")

    plain_text_output = "\n".join(filtered_configs)
    safe_write(Config.OUTPUT_PLAIN_PATH, plain_text_output)
    logging.info(f"Wrote {len(filtered_configs)} nodes to {Config.OUTPUT_PLAIN_PATH}")

    subscription_content = base64.b64encode(\n.join(filtered_configs).encode()).decode()
    safe_write(Config.OUTPUT_BASE64_PATH, subscription_content)
    logging.info(f"Wrote base64 subscription to {Config.OUTPUT_BASE64_PATH}")

    report_str = get_report_string(filtered_configs, metrics_map)
    safe_write(Config.OUTPUT_REPORT_PATH, report_str)
    logging.info(f"Wrote detailed report to {Config.OUTPUT_REPORT_PATH}")
    
    history_manager.save_history()
    
    print("\n----- V2Ray Scanner Ultimate Finished -----")
    print(f"- Found {len(filtered_configs)} high-quality nodes.")
    print(f"- Subscriptions saved to: {Config.OUTPUT_DIR}")
    print(f"- Detailed report: {Config.OUTPUT_REPORT_PATH}")
    print("-------------------------------------------")

def main() -> None:
    """The synchronous entrypoint for the asyncio runner."""
    if not validate_config():
        sys.exit(1)

    try:
        asyncio.run(run_once())
    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
        print("\nProcess cancelled by user.")
    except Exception as e:
        logging.critical("An unhandled error occurred in the main process", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
