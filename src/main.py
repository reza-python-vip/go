from __future__ import annotations

import asyncio
import base64
import logging
import sys
from typing import List, Type

import uvicorn
try:
    from tqdm.asyncio import tqdm  # optional dependency
except Exception:  # pragma: no cover - fallback when tqdm isn't installed
    def tqdm(iterable, **kwargs):
        """Fallback tqdm: returns the iterable unchanged when tqdm is not available."""
        return iterable

from .config import config
from .fetcher import fetch_subscription_links
from .filter import filter_and_rank
from .health import app as health_app
from .history import HistoryManager
from .models import Node, NodeMetrics
from .tester_base import NodeTester
from .parsers import parse_links
from .reporter import generate_report
from .utils import safe_write
from .xray_tester import XrayTester
from .hiddify_tester import HiddifyTester

# --- Logging Setup ---
logging.basicConfig(
    level=config.LOG_LEVEL.upper(),
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_tester_class() -> Type[NodeTester]:
    """Factory to get the tester class based on config."""
    tester_name = config.TESTER.lower()
    if tester_name == "xray":
        return XrayTester
    if tester_name == "hiddify":
        return HiddifyTester
    raise ValueError(f"Invalid tester specified: '{config.TESTER}'")

async def test_all_nodes(
    tester_class: Type[NodeTester],
    nodes: List[Node],
    port_manager: PortManager,
) -> List[NodeMetrics]:
    """Tests a list of nodes concurrently using the specified tester class."""
    metrics_list = []
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_TESTS)

    async def test_with_semaphore(node: Node):
        async with semaphore:
            async with tester_class(config, port_manager) as tester:
                return await tester.test_node(node)

    tasks = [test_with_semaphore(node) for node in nodes]
    progress = tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f"Testing via {config.TESTER}")

    for future in progress:
        try:
            metrics = await future
            if metrics:
                metrics_list.append(metrics)
        except Exception as e:
            logger.error(f"A node test resulted in an unhandled exception: {e}", exc_info=True)

    return metrics_list

async def run_scanner():
    """The main coroutine to run the complete scanner workflow."""
    logger.info("🚀 Starting scanner run...")
    health_app.main_loop_active = True

    history = HistoryManager()
    await history.load()

    links = await fetch_subscription_links()
    nodes = parse_links(links)
    logger.info(f"Total unique nodes found: {len(nodes)}")

    if not nodes:
        logger.warning("No nodes to test. Skipping tests.")
        return

    tester_class = get_tester_class()
    port_manager = PortManager(start=config.XRAY_SOCKS_PORT_START, end=config.XRAY_SOCKS_PORT_END)
    metrics = await test_all_nodes(tester_class, nodes, port_manager)
    logger.info(f"Testing complete. {sum(1 for m in metrics if m.success)} nodes passed.")

    for m in metrics:
        history.update(m.node_id, m.success)

    final_nodes = filter_and_rank(nodes, metrics, history, config)

    if final_nodes:
        # Generate and save subscription file
        subscription_content = "\n".join(node.config for node in final_nodes)
        encoded_content = base64.b64encode(subscription_content.encode("utf-8")).decode("utf-8")
        safe_write(config.OUTPUT_SUBSCRIPTION_PATH, encoded_content)
        logger.info(f"Saved {len(final_nodes)} nodes to subscription file.")

        # Generate and save report
        report_content = generate_report(final_nodes, metrics)
        safe_write(config.OUTPUT_REPORT_PATH, report_content)
        logger.info("Generated and saved Markdown report.")
    else:
        logger.warning("No high-quality nodes found after filtering.")

    await history.save()
    logger.info("✅ Scanner run finished.")
    health_app.main_loop_active = False

async def main_loop():
    """Runs the scanner in a loop with a configured interval."""
    while True:
        await run_scanner()
        if config.RUN_INTERVAL_MINUTES <= 0:
            break
        logger.info(f"Waiting for {config.RUN_INTERVAL_MINUTES} minutes...")
        await asyncio.sleep(config.RUN_INTERVAL_MINUTES * 60)

async def start_health_server():
    """Starts the Uvicorn health check server."""
    uv_config = uvicorn.Config(health_app, host="0.0.0.0", port=config.HEALTH_CHECK_PORT, log_level="warning")
    server = uvicorn.Server(uv_config)
    await server.serve()

def main():
    """Synchronous entrypoint to start the application."""
    try:
        # Ensure output directories exist
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if len(sys.argv) > 1 and sys.argv[1] == "health":
            asyncio.run(start_health_server())
        else:
            health_task = asyncio.create_task(start_health_server())
            main_task = asyncio.create_task(main_loop())
            
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(health_task, main_task))

    except KeyboardInterrupt:
        logger.info("User interrupted. Shutting down.")
    except (ValueError, FileNotFoundError) as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical("An unexpected critical error occurred.", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
