"""Node tester implementation using the Xray-core binary.

This module provides a concrete implementation of the `NodeTester` ABC, leveraging
the Xray-core command-line tool to perform detailed network tests and extract metrics.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, Optional

import aiohttp
import aiosocks

from .network_metrics import Metrics
from .tester_base import NodeTester
from .config import Config
from .utils import get_node_id

class XrayProcessManager:
    """Manages the lifecycle of an Xray subprocess."""

    def __init__(self, binary_path: str, config_path: str):
        self.binary_path = binary_path
        self.config_path = config_path
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def start(self) -> bool:
        """Starts the Xray process and returns True on success."""
        try:
            cmd = [self.binary_path, "-c", self.config_path]
            self.proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.sleep(Config.XRAY_STARTUP_DELAY)

            if self.proc.returncode is not None:
                stderr = (await self.proc.stderr.read()).decode(errors='ignore')
                self.logger.warning(f"Xray process failed to start. Stderr: {stderr}")
                return False
            self.logger.debug("Xray process started successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Exception starting Xray process: {e}", exc_info=True)
            return False

    async def stop(self) -> None:
        """Stops the Xray process if it is running."""
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.terminate()
                await asyncio.wait_for(self.proc.wait(), timeout=5)
                self.logger.debug("Xray process terminated.")
            except asyncio.TimeoutError:
                self.proc.kill()
                await self.proc.wait()
                self.logger.warning("Xray process was killed forcefully.")
            except Exception as e:
                self.logger.error(f"Error stopping Xray process: {e}", exc_info=True)

class XrayTester(NodeTester):
    """A NodeTester that uses the Xray-core binary to test proxy nodes."""

    SOCKS_PORT = 10808
    TEST_URL = Config.TEST_URL
    DOWNLOAD_BYTES = Config.DOWNLOAD_SIZE_BYTES

    def __init__(self, xray_binary_path: str, cache_dir: str, http_timeout: int):
        self.binary_path = xray_binary_path
        self.cache_dir = cache_dir
        self.http_timeout = http_timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    def _generate_config(self, config_line: str) -> Optional[Dict[str, Any]]:
        """Generates a valid Xray JSON configuration from a single node URL."""
        try:
            from .parsers import parse_v2ray_uri
            
            outbound_settings = parse_v2ray_uri(config_line)
            if not outbound_settings:
                self.logger.debug(f"Could not parse URI: {config_line[:40]}...")
                return None

            return {
                "log": {"loglevel": "warning"},
                "inbounds": [{
                    "port": self.SOCKS_PORT,
                    "protocol": "socks",
                    "listen": "127.0.0.1",
                    "settings": {"auth": "noauth", "udp": False}
                }],
                "outbounds": [outbound_settings],
            }
        except Exception as e:
            self.logger.error(f"Failed to generate Xray config for {config_line[:40]}: {e}", exc_info=True)
            return None

    async def test_node(self, config_line: str) -> Optional[Metrics]:
        """Tests a single proxy configuration and returns its metrics."""
        node_id = get_node_id(config_line)
        xray_config_obj = self._generate_config(config_line)
        if not xray_config_obj:
            return Metrics(success=False)

        with tempfile.NamedTemporaryFile('w', delete=False, suffix=".json", dir=self.cache_dir) as f:
            config_path = f.name
            json.dump(xray_config_obj, f)
        
        manager = XrayProcessManager(self.binary_path, config_path)
        try:
            if not await manager.start():
                return Metrics(success=False)
            
            return await self._measure_performance()
        except Exception as e:
            self.logger.error(f"Error during test of node {node_id}: {e}", exc_info=True)
            return Metrics(success=False)
        finally:
            await manager.stop()
            if os.path.exists(config_path):
                os.remove(config_path)

    async def _measure_performance(self) -> Metrics:
        """Measures latency and throughput by downloading a file."""
        try:
            proxy_url = f"socks5://127.0.0.1:{self.SOCKS_PORT}"
            timeout = aiohttp.ClientTimeout(total=self.http_timeout)

            async with aiohttp.ClientSession() as session:
                start_time = time.monotonic()
                async with session.get(self.TEST_URL, proxy=proxy_url, timeout=timeout) as response:
                    if response.status != 200:
                        return Metrics(success=False)
                    
                    latency = (time.monotonic() - start_time) * 1000

                    download_start = time.monotonic()
                    content = await response.content.read()
                    download_time = time.monotonic() - download_start

                    if download_time > 0 and len(content) == self.DOWNLOAD_BYTES:
                        throughput = (self.DOWNLOAD_BYTES / download_time) / 1024 # KB/s
                        jitter = abs(latency - ((time.monotonic() - start_time) * 1000 - latency))/2
                    else:
                        return Metrics(success=False, latency_ms=latency)

            return Metrics(
                success=True,
                latency_ms=latency,
                jitter_ms=jitter,
                throughput_kbps=throughput
            )
        except (aiosocks.errors.ProxyError, asyncio.TimeoutError) as e:
            self.logger.debug(f"Measurement failed: {e}")
            return Metrics(success=False)
        except Exception as e:
            self.logger.error(f"Unexpected error in measurement: {e}", exc_info=True)
            return Metrics(success=False)

    async def __aenter__(self):
        if not os.path.exists(self.binary_path) or not os.access(self.binary_path, os.X_OK):
            raise FileNotFoundError(f"Xray binary not found or not executable at {self.binary_path}")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.logger.info("XrayTester initialized.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("XrayTester shutting down.")
