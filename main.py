from __future__ import annotations

import asyncio
import logging
import os
import signal
import threading
from pathlib import Path

import uvicorn

from src.utils.logging import setup_logging

from src.config import Config
from src.fetcher import SubscriptionFetcher
from src.filter import filter_and_rank
from src.health import app as health_app
from src.history import HistoryManager
from src.models import Node
from src.reporter import generate_report
from src.utils import safe_write
from src.xray_tester import PortManager, XrayTester

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_once(config: Config, history: HistoryManager, tester: XrayTester):
    """Perform a single, complete scan and reporting cycle."""
    health_app.main_loop_active = True
    logger.info("Starting new scan cycle...")

    # 1. Fetch Nodes
    fetcher = SubscriptionFetcher(config.SUBSCRIPTION_SOURCES)
    raw_configs = await fetcher.fetch_all()
    nodes = [Node(config=c) for c in raw_configs]
    logger.info(f"Fetched {len(nodes)} unique nodes.")

    if not nodes:
        logger.warning("No nodes fetched, skipping test cycle.")
        return

    # 2. Test Nodes
    test_tasks = [tester.test_node(node) for node in nodes]
    all_metrics = await asyncio.gather(*test_tasks)
    logger.info(f"Finished testing {len(all_metrics)} nodes.")

    # 3. Update History
    for metric in all_metrics:
        history.update_node_history(metric.node_id, metric.success)

    # 4. Filter and Rank
    ranked_nodes = filter_and_rank(nodes, all_metrics, history, config)
    logger.info(f"Found {len(ranked_nodes)} high-quality nodes.")

    # 5. Generate Report and Subscription
    report_content = generate_report(ranked_nodes, all_metrics)
    hq_configs = [node.config for node in ranked_nodes]
    subscription_content = "\n".join(hq_configs)

    # 6. Write to Files
    await safe_write(Path(config.OUTPUT_REPORT_PATH), report_content)
    await safe_write(Path(config.OUTPUT_SUBSCRIPTION_PATH), subscription_content)
    logger.info(f"Report and subscription files updated at '{config.OUTPUT_DIR}'.")

    # 7. Save History
    await history.save_history()
    health_app.main_loop_active = False
    logger.info("Scan cycle completed.")


async def main():
    """Main application entry point."""
    # Setup logging
    log_file = os.path.join("logs", "scanner.log") if os.path.isdir("logs") else None
    setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"), log_file=log_file)

    config = Config()
    history = HistoryManager(Path(config.OUTPUT_DIR))
    await history.load_history()

    port_manager = PortManager(config.XRAY_SOCKS_PORT_START, config.XRAY_SOCKS_PORT_END)
    tester = XrayTester(config, port_manager)

    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received, initiating graceful shutdown...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    # Start health check server in a separate thread
    health_server_thread = threading.Thread(
        target=uvicorn.run,
        args=(health_app,),
        kwargs={
            "host": "0.0.0.0",
            "port": config.HEALTH_CHECK_PORT,
            "log_level": "warning",
        },
        daemon=True,
    )
    health_server_thread.start()

    # Main execution loop
    while not shutdown_event.is_set():
        try:
            await run_once(config, history, tester)
        except Exception as e:
            logger.critical(
                f"An unhandled error occurred in the main loop: {e}", exc_info=True
            )

        # Wait for the next interval or for the shutdown signal
        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=config.RUN_INTERVAL_MINUTES * 60
            )
        except asyncio.TimeoutError:
            pass  # This is expected, continue to next cycle

    logger.info("Shutting down... Final history save.")
    await history.save_history()
    logger.info("Application has shut down gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
