from __future__ import annotations


import asyncio
import logging
from typing import Any, Dict

import aiohttp

from .config import Config
from .models import Node, NodeMetrics
from .utils import get_open_port
from .xray_tester import PortManager

logger = logging.getLogger(__name__)


class HiddifyTester:
    """A node tester utilizing the Hiddify-Core binary."""

    def __init__(self, config: Config, port_manager: PortManager):
        self.config = config
        self.port_manager = port_manager
        self.process = None
        self.rpc_port = None
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.HTTP_TIMEOUT)
        )

    async def __aenter__(self):
        self.rpc_port = get_open_port()
        cmd = [
            str(self.config.HIDDIFY_BINARY),
            "run",
            "--config",
            'memory:{"log":{"level":"warn"}}',
            "--experimental",
            "rpc-server",
            "--experimental-rpc-server-addr",
            f"127.0.0.1:{self.rpc_port}",
        ]
        logger.info("Starting Hiddify-Core process on RPC port %s", self.rpc_port)
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(1)  # Give it a moment to start up
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.process and self.process.returncode is None:
            logger.info("Terminating Hiddify-Core process.")
            self.process.terminate()
            await self.process.wait()
        if self.session:
            await self.session.close()
        logger.info("HiddifyTester shut down.")

    async def _rpc_call(
        self, method: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Executes a JSON-RPC call to the Hiddify-Core process."""
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        url = f"http://127.0.0.1:{self.rpc_port}/jsonrpc"
        try:
            async with self.session.post(url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                if "error" in result:
                    raise RuntimeError(f"RPC Error: {result['error']}")
                return result.get("result", {})
        except aiohttp.ClientError as e:
            logger.error(f"RPC call '{method}' failed: {e}")
            raise

    def _get_remark(self, node: Node) -> str:
        """Extracts the remark from the node config."""
        try:
            return node.config.split("#")[1]
        except IndexError:
            return ""

    async def test_node(self, node: Node) -> NodeMetrics:
        """Tests a single node and returns its metrics."""
        socks_port = await self.port_manager.get_port()
        latency_ms = -1
        throughput_kbps = -1
        success = False

        try:
            # 1. Select the proxy
            await self._rpc_call(
                "proxy.select", {"tag": "outbound", "proxy": node.config}
            )

            # 2. Test latency
            latency_result = await self._rpc_call(
                "proxy.urltest",
                {"tag": "outbound", "url": self.config.LATENCY_TEST_URL},
            )
            latency_ms = latency_result.get("delay", -1)

            if latency_ms > 0 and latency_ms < self.config.MAX_LATENCY_MS:
                # 3. Test throughput if latency is acceptable
                speed_result = await self._rpc_call(
                    "proxy.urltest",
                    {"tag": "outbound", "url": self.config.SPEED_TEST_URL},
                )
                download_kbps = speed_result.get("download_speed", 0) / 1024

                if download_kbps > self.config.MIN_THROUGHPUT_KBPS:
                    throughput_kbps = download_kbps
                    success = True
                    logger.debug(
                        self._get_remark(node),
                        latency_ms,
                        throughput_kbps,
                    )
                else:
                    logger.debug(
                        "Node %s failed speed test: %.2f KB/s",
                        self._get_remark(node),
                        download_kbps,
                    )
            else:
                logger.debug(
                    "Node %s failed latency test: %sms", self._get_remark(node), latency_ms
                )

        except (RuntimeError, aiohttp.ClientError) as e:
            logger.warning("Test failed for node %s: %s", self._get_remark(node), e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred testing %s: %s",
                self._get_remark(node),
                e,
                exc_info=True,
            )
        finally:
            await self.port_manager.release_port(socks_port)

        return NodeMetrics(
            node_id=node.node_id,
            success=success,
            latency_ms=latency_ms,
            throughput_kbps=throughput_kbps,
        )
