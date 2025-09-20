from __future__ import annotations

import base64
import logging
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def safe_write(path: Path, content: str) -> None:
    """Asynchronously writes content to a file, creating parent directories."""
    try:
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_text, content, encoding="utf-8")
        logger.debug(f"Successfully wrote to file: {path}")
    except IOError as e:
        logger.error(f"Could not write to file {path}: {e}")


def decode_base64_text(encoded_text: str) -> Optional[str]:
    """Decodes a base64 encoded string, gracefully handling common errors."""
    # Ignore data URIs or non-base64 lines
    if not encoded_text or encoded_text.startswith(("data:", "#")):
        return None

    try:
        # Add padding if it's missing
        padding = len(encoded_text) % 4
        if padding != 0:
            encoded_text += "=" * (4 - padding)

        decoded_bytes = base64.b64decode(encoded_text)
        return decoded_bytes.decode("utf-8")

    except (ValueError, TypeError, base64.binascii.Error):
        # Not a valid base64 string, might be a regular config line
        return None
    except UnicodeDecodeError as e:
        logger.warning(f"Could not decode bytes to UTF-8 after base64 decoding: {e}")
        return None
