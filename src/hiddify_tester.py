"""Node tester implementation using the Hiddify-Core binary.

This module provides a concrete implementation of the NodeTester abstract base class,
leveraging the Hiddify-Core command-line tool to perform network tests.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from typing import Optional

from .config import Config
from .network_metrics import Metrics
from .tester_base import NodeTester


class HiddifyTester(NodeTester):
    """A NodeTester that uses the Hiddify-Core binary to test proxy nodes."""

    def __init__(self, hiddify_binary_path: str, cache_dir: str, http_timeout: int):
        self.binary_path = hiddify_binary_path
        self.cache_dir = cache_dir
        self.http_timeout = http_timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    async def test_node(self, config_line: str) -> Optional[Metrics]:
        """Tests a single proxy configuration using Hiddify-Core and returns its metrics."""
        if not config_line:
            return None

        # Hiddify-Core expects the config via a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json", dir=self.cache_dir) as tmp_config_file:
            tmp_config_path = tmp_config_file.name
            # The tool expects a JSON object with a 'proxies' list
            json.dump({"proxies": [config_line]}, tmp_config_file)
        
        # Prepare the command to run
        # The command syntax for Hiddify might be different; this is an assumed example.
        # Example: hiddify-core -c <config_file> -t <timeout> --test-url <url>
        cmd = [
            self.binary_path,
            "-c", tmp_config_path,
            "-t", str(self.http_timeout),
            "--test-url", "http://www.google.com/gen_204"  # A common URL for connectivity checks
        ]
        self.logger.debug(f"Executing command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.http_timeout + 5)

            if process.returncode != 0:
                self.logger.error(f"Hiddify process exited with code {process.returncode}. Stderr: {stderr.decode(errors='ignore')}")
                return None
            
            # Assuming Hiddify-Core outputs metrics in a JSON format to stdout
            # This part needs to be adapted based on the actual output of the tool
            try:
                result = json.loads(stdout.decode())
                # Example structure: {"latency": 120, "throughput": 5000, "loss": 0.1}
                metrics = Metrics(
                    latency_ms=result.get('latency'),
                    jitter_ms=None,  # Hiddify might not provide this
                    packet_loss=result.get('loss'),
                    throughput_kbps=result.get('throughput'),
                    success=True
                )
                return metrics
            except json.JSONDecodeError:
                self.logger.error("Failed to decode JSON from Hiddify output.")
                return None

        except asyncio.TimeoutError:
            self.logger.warning(f"Test timed out for node: {config_line[:50]}...")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while testing node: {e}")
            return None
        finally:
            # Clean up the temporary config file
            if os.path.exists(tmp_config_path):
                os.remove(tmp_config_path)

    async def __aenter__(self):
        """Check for binary existence on entry."""
        if not os.path.exists(self.binary_path) or not os.access(self.binary_path, os.X_OK):
            raise FileNotFoundError(f"Hiddify binary not found or not executable at {self.binary_path}")
        self.logger.info("HiddifyTester initialized and binary found.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources on exit."""
        self.logger.info("HiddifyTester shutting down.")
