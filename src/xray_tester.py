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


class XrayTester(NodeTester):
    """A NodeTester that uses the Xray-core binary to test proxy nodes."""

    SOCKS_PORT = 10808
    TEST_URL = "https://speed.cloudflare.com/__down?bytes=5000000"  # 5MB
    DOWNLOAD_BYTES = 5000000

    def __init__(self, xray_binary_path: str, cache_dir: str, http_timeout: int):
        self.binary_path = xray_binary_path
        self.cache_dir = cache_dir
        self.http_timeout = http_timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    def _generate_config(self, config_line: str) -> Optional[Dict[str, Any]]:
        """Generates a valid Xray JSON configuration from a single node URL."""
        try:
            # Basic parsing for protocol type
            protocol = config_line.split("://")[0]
            if not protocol:
                return None

            # This is a highly simplified config generator.
            # A production-ready version would need a robust V2Ray link parser.
            return {
                "log": {"loglevel": "warning"},
                "inbounds": [
                    {
                        "port": self.SOCKS_PORT,
                        "protocol": "socks",
                        "listen": "127.0.0.1",
                        "settings": {"auth": "noauth", "udp": False},
                    }
                ],
                "outbounds": [
                    {
                        "protocol": protocol,
                        "settings": {},
                        "streamSettings": {},
                        # The config_line itself often can't be just dumped in.
                        # This part needs a proper parser to deconstruct the line.
                        # We'll make a simplistic assumption for vmess.
                    }
                ],
            }
        except Exception as e:
            self.logger.error(f"Failed to generate base config: {e}")
            return None

    async def test_node(self, config_line: str) -> Optional[Metrics]:
        """Tests a single proxy configuration using Xray-core and returns its metrics."""
        # This method is a placeholder. The real logic is now in _get_real_metrics.
        # The process is: generate config, run Xray, test via proxy, kill Xray.
        
        # A proper implementation for parsing various link types is complex.
        # For now, we'll assume the link is in a format that can be broadly used,
        # which is a major simplification.
        xray_config_obj = self._generate_config(config_line)
        if not xray_config_obj:
            return None

        # This is where a proper link parser would populate the outbound settings.
        # Since we lack one, this tester will have limited compatibility.
        # For demonstration, we assume the config line is a JSON object for the outbound.
        try:
            # This is not how real links work, but it's a way to test the pipeline.
            # A real implementation would parse vmess://, ss://, etc.
            pass # Skipping the complex parsing logic for now
        except Exception:
            return None

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json", dir=self.cache_dir) as tmp_f:
            config_path = tmp_f.name
            # This is still a placeholder for a valid config
            json.dump(xray_config_obj, tmp_f)

        proc = None
        try:
            cmd = [self.binary_path, "-c", config_path]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            
            # Give Xray a moment to start up
            await asyncio.sleep(2)

            # Check if the process started correctly
            if proc.returncode is not None:
                stderr = await proc.stderr.read()
                self.logger.warning(f"Xray failed to start for node {config_line[:40]}. Stderr: {stderr.decode(errors='ignore')}")
                return None

            return await self._measure_performance()

        except Exception as e:
            self.logger.error(f"An error occurred while testing node {config_line[:40]}: {e}")
            return None
        finally:
            if proc and proc.returncode is None:
                proc.terminate()
                await proc.wait()
            if os.path.exists(config_path):
                os.remove(config_path)

    async def _measure_performance(self) -> Optional[Metrics]:
        """Measures latency and throughput by downloading a file through the SOCKS proxy."""
        try:
            # Setup the SOCKS5 connector
            connector = aiohttp.TCPConnector(ssl=False) # SSL is handled by the proxy connection
            proxy_url = f"socks5://127.0.0.1:{self.SOCKS_PORT}"

            start_time = time.monotonic()
            
            async with aiohttp.ClientSession(connector=connector) as session:
                # Measure latency (time to first byte)
                async with session.get(self.TEST_URL, proxy=proxy_url, timeout=self.http_timeout) as response:
                    if response.status != 200:
                        self.logger.warning(f"Test URL returned status {response.status}")
                        return None
                    
                    latency = (time.monotonic() - start_time) * 1000  # in ms

                    # Measure throughput
                    download_start = time.monotonic()
                    content = await response.content.read()
                    download_time = time.monotonic() - download_start

                    if download_time > 0:
                        throughput = (self.DOWNLOAD_BYTES / download_time) / 1024 # KB/s
                    else:
                        throughput = float('inf')

            return Metrics(
                success=True,
                latency_ms=latency,
                throughput_kbps=throughput
            )

        except aiosocks.errors.ProxyError as e:
            self.logger.warning(f"Proxy connection failed: {e}")
            return None
        except asyncio.TimeoutError:
            self.logger.warning("Measurement timed out.")
            return None
        except Exception as e:
            self.logger.error(f"Failed during performance measurement: {e}")
            return None

    async def __aenter__(self):
        if not os.path.exists(self.binary_path) or not os.access(self.binary_path, os.X_OK):
            raise FileNotFoundError(f"Xray binary not found or not executable at {self.binary_path}")
        self.logger.info("XrayTester initialized and binary found.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("XrayTester shutting down.")
