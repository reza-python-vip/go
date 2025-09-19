from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Optional

from .exceptions import (
    ConnectionTestError,
    XrayConfigError,
    XrayStartupError,
)

import aiohttp

from .config import Config
from .models import Node, NodeMetrics
from .parsers import parse_v2ray_uri

logger = logging.getLogger(__name__)

class PortManager:
    """A simple manager to avoid port conflicts during concurrent tests."""
    def __init__(self, start_port: int, end_port: int):
        self._ports = asyncio.Queue()
        for port in range(start_port, end_port + 1):
            self._ports.put_nowait(port)

    async def get_port(self) -> int:
        """Get an available port."""
        return await self._ports.get()

    async def release_port(self, port: int):
        """Release a port back to the pool."""
        await self._ports.put(port)

class XrayManager:
    """Manages the lifecycle of an Xray subprocess for a single test."""

    def __init__(self, binary_path: str, node: Node, port: int, temp_dir: str):
        self.binary_path = binary_path
        self.node = node
        self.port = port
        self.temp_dir = temp_dir
        self.config_path: Optional[str] = None
        self.process: Optional[asyncio.subprocess.Process] = None

    async def __aenter__(self) -> XrayManager:
        self.config_path = await self._create_config_file()
        if not self.config_path:
            raise XrayConfigError(f"Failed to parse or create config for node {self.node.node_id}")

        if not os.path.exists(self.binary_path):
            raise XrayStartupError(f"Xray binary not found at {self.binary_path}")

        cmd = [self.binary_path, "-c", self.config_path]
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        except (OSError, asyncio.SubprocessError) as e:
            raise XrayStartupError(f"Failed to start Xray process: {e}")

        try:
            # Wait for Xray to start by checking if the SOCKS port is open
            await self._wait_for_port(self.port, timeout=5.0)
            logger.debug(f"Xray process started for node {self.node.node_id} on port {self.port}")
            return self
        except asyncio.TimeoutError:
            stderr = await self.process.stderr.read()
            error_msg = stderr.decode(errors='ignore')
            logger.warning(f"Xray for {self.node.node_id} failed to start: {error_msg}")
            await self.__aexit__(None, None, None)  # Ensure cleanup
            raise XrayStartupError(f"Xray process failed to start: {error_msg}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.config_path and os.path.exists(self.config_path):
            try:
                os.remove(self.config_path)
            except OSError:
                pass

    async def _create_config_file(self) -> Optional[str]:
        outbound_config = parse_v2ray_uri(self.node.config)
        if not outbound_config:
            return None

        xray_config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": self.port,
                "protocol": "socks",
                "listen": "127.0.0.1",
                "settings": {"auth": "noauth", "udp": True, "ip": "127.0.0.1"},
            }],
            "outbounds": [outbound_config],
        }

        fd, path = tempfile.mkstemp(suffix=".json", dir=self.temp_dir)
        os.close(fd)
        async with asyncio.to_thread(lambda: open(path, 'w')) as f:
            await asyncio.to_thread(json.dump, xray_config, f)
        return path

    @staticmethod
    async def _wait_for_port(port: int, timeout: float):
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", port), timeout=1.0
                )
                writer.close()
                await writer.wait_closed()
                return
            except (ConnectionRefusedError, asyncio.TimeoutError):
                await asyncio.sleep(0.1)
        raise asyncio.TimeoutError(f"Port {port} did not open in time.")

class XrayTester:
    """A NodeTester that uses the Xray-core binary to test proxy nodes."""

    def __init__(self, config: Config, port_manager: PortManager):
        self.config = config
        self.port_manager = port_manager
        if not os.path.isfile(self.config.XRAY_BINARY):
            raise FileNotFoundError(f"Xray binary not found at {self.config.XRAY_BINARY}")

    async def test_node(self, node: Node) -> NodeMetrics:
        port = await self.port_manager.get_port()
        try:
            async with XrayManager(self.config.XRAY_BINARY, node, port, self.config.TEMP_DIR):
                metrics = await self._perform_tests(port)
                return NodeMetrics(node_id=node.node_id, **metrics)
        except XrayConfigError as e:
            logger.warning(f"Configuration error for node {node.node_id}: {e}")
            return NodeMetrics(node_id=node.node_id, success=False, error="config_error")
        except XrayStartupError as e:
            logger.warning(f"Startup error for node {node.node_id}: {e}")
            return NodeMetrics(node_id=node.node_id, success=False, error="startup_error")
        except ConnectionTestError as e:
            logger.warning(f"Connection test failed for node {node.node_id}: {e}")
            return NodeMetrics(node_id=node.node_id, success=False, error="connection_error")
        except Exception as e:
            logger.error(f"Unexpected error testing node {node.node_id}: {e}", exc_info=True)
            return NodeMetrics(node_id=node.node_id, success=False, error="unknown_error")
        finally:
            await self.port_manager.release_port(port)

    async def _perform_tests(self, port: int) -> dict:
        proxy_url = f"socks5://127.0.0.1:{port}"
        timeout = aiohttp.ClientTimeout(total=self.config.HTTP_TIMEOUT)

        try:
            latency = await self._measure_latency(proxy_url, timeout)
            throughput = await self._measure_throughput(proxy_url, timeout)
            return {"success": True, "latency_ms": latency, "throughput_kbps": throughput}
        except aiohttp.ClientConnectorError as e:
            logger.debug(f"Connection error on port {port}: {e}")
            raise ConnectionTestError(f"Failed to connect: {e}")
        except aiohttp.ClientResponseError as e:
            logger.debug(f"HTTP error on port {port}: {e.status}")
            raise ConnectionTestError(f"HTTP error {e.status}")
        except asyncio.TimeoutError:
            logger.debug(f"Connection timeout on port {port}")
            raise ConnectionTestError("Connection timeout")
        except Exception as e:
            logger.error(f"Unexpected error in connection test on port {port}: {e}", exc_info=True)
            raise ConnectionTestError(f"Unknown error: {e}")

    async def _measure_latency(self, proxy_url: str, timeout: aiohttp.ClientTimeout) -> float:
        url = self.config.LATENCY_TEST_URL
        if not url:
            raise XrayConfigError("LATENCY_TEST_URL not configured")

        start_time = time.monotonic()
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, proxy=proxy_url) as response:
                    response.raise_for_status()
                    await response.read()  # Consume body to get accurate timing
            return (time.monotonic() - start_time) * 1000
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.debug(f"Latency test failed after {elapsed:.2f}ms: {e}")
            raise ConnectionTestError(f"Latency test failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in latency test: {e}", exc_info=True)
            raise ConnectionTestError(f"Latency test error: {e}")

    async def _measure_throughput(self, proxy_url: str, timeout: aiohttp.ClientTimeout) -> float:
        url = self.config.SPEED_TEST_URL
        start_time = time.monotonic()
        bytes_downloaded = 0
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, proxy=proxy_url) as response:
                response.raise_for_status()
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    bytes_downloaded += len(chunk)
        duration = time.monotonic() - start_time
        if duration == 0: return 0.0
        return (bytes_downloaded * 8) / duration / 1024 # Kbps
