
"""
Utility functions used across the project.

This package provides `safe_write` and `decode_base64_text` so other
modules can reliably import `from .utils import decode_base64_text` even
when a `src/utils.py` module also exists.
Also provides PortManager and get_open_port for port allocation.
"""

from __future__ import annotations
import asyncio
import base64
import logging
import socket
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

async def safe_write(path: Path, content: str) -> None:
	"""Asynchronously writes content to a file, creating parent directories."""
	try:
		await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
		await asyncio.to_thread(path.write_text, content, encoding='utf-8')
		logger.debug("Successfully wrote to file: %s", path)
	except IOError as e:
		logger.error("Could not write to file %s: %s", path, e)

def decode_base64_text(encoded_text: str) -> Optional[str]:
	"""Decodes a base64 encoded string, gracefully handling common errors."""
	# Ignore data URIs or non-base64 lines
	if not encoded_text or encoded_text.startswith(("data:", "#")):
		return None
	try:
		# Add padding if it's missing
		padding = len(encoded_text) % 4
		if padding != 0:
			encoded_text += '=' * (4 - padding)
		decoded_bytes = base64.b64decode(encoded_text)
		return decoded_bytes.decode('utf-8')
	except UnicodeDecodeError as e:
		logger.warning("Could not decode bytes to UTF-8 after base64 decoding: %s", e)
		return None
	except (ValueError, TypeError, base64.binascii.Error):
		# Not a valid base64 string, might be a regular config line
		return None

class PortManager:
	"""A simple manager to allocate ports from a range."""
	def __init__(self, start: int = 20000, end: int = 21000):
		self.start = start
		self.end = end
		self._next = start

	def get_port(self) -> int:
		"""Get the next available port in the range, wrapping around if necessary."""
		port = self._next
		self._next += 1
		if self._next > self.end:
			self._next = self.start
		return port

def get_open_port() -> int:
	"""Return an available ephemeral port from the OS."""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind(("", 0))
		return s.getsockname()[1]

__all__ = ["decode_base64_text", "safe_write", "PortManager", "get_open_port"]
