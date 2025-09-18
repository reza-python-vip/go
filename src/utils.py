"""General utility functions used across the project.

This module contains helper functions for file I/O, data encoding/decoding,
and other common tasks that are not specific to any single component.
"""

from __future__ import annotations

import base64
import logging
import os
import hashlib
from urllib.parse import urlparse
from typing import Optional

# Get a logger for this module
logger = logging.getLogger(__name__)


def safe_write(path: str, content: str) -> None:
    """Writes content to a file, creating parent directories if they don't exist."""
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"Successfully wrote to file: {path}")
    except IOError as e:
        logger.error(f"Could not write to file {path}: {e}")

def get_node_id(config: str) -> str:
    """Generates a unique and stable identifier for a node configuration."""
    base_config = config.split('#')[0].strip()
    parsed = urlparse(base_config)
    
    # Use hostname and port for a stable ID. This identifies the server.
    if parsed.hostname and parsed.port:
        # For protocols like ws or grpc, path can also be significant.
        if parsed.scheme in ['ws', 'grpc'] and parsed.path and parsed.path != '/':
            identifier = f"{parsed.hostname}:{parsed.port}:{parsed.path}"
        else:
            identifier = f"{parsed.hostname}:{parsed.port}"
    else:
        # Fallback for non-standard URIs
        identifier = base_config
        
    return hashlib.sha1(identifier.encode('utf-8')).hexdigest()


def decode_base64_text(encoded_text: str) -> Optional[str]:
    """Decodes a base64 encoded string, gracefully handling common errors."""
    try:
        padding = len(encoded_text) % 4
        if padding != 0:
            encoded_text += '=' * (4 - padding)
        decoded_bytes = base64.b64decode(encoded_text)
        return decoded_bytes.decode('utf-8')
    except (ValueError, TypeError, base64.binascii.Error) as e:
        logger.debug(f"Failed to decode base64 string: {e}")
        return None
    except UnicodeDecodeError as e:
        logger.warning(f"Could not decode bytes to UTF-8 after base64 decoding: {e}")
        return None
