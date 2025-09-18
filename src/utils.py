"""General utility functions used across the project.

This module contains helper functions for file I/O, data encoding/decoding,
and other common tasks that are not specific to any single component.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

# Get a logger for this module
logger = logging.getLogger(__name__)


def safe_write(path: str, content: str) -> None:
    """Writes content to a file, creating parent directories if they don't exist.

    This function prevents errors that occur when trying to write to a file in a
    non-existent directory.

    Args:
        path: The full path to the file to be written.
        content: The string content to write to the file.
    """
    try:
        # Ensure the directory exists
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        # Write the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"Successfully wrote to file: {path}")

    except IOError as e:
        logger.error(f"Could not write to file {path}: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred in safe_write for path {path}: {e}")


def decode_base64_text(encoded_text: str) -> Optional[str]:
    """Decodes a base64 encoded string, gracefully handling common errors.

    This function attempts to decode a base64 string and handles issues like
    incorrect padding or invalid characters.

    Args:
        encoded_text: The base64 encoded string.

    Returns:
        The decoded string if successful, otherwise None.
    """
    try:
        # Add padding if it's missing. Base64 strings must be a multiple of 4.
        padding = len(encoded_text) % 4
        if padding != 0:
            encoded_text += '=' * (4 - padding)
        
        # Decode the string
        decoded_bytes = base64.b64decode(encoded_text)
        return decoded_bytes.decode('utf-8')
    
    except (ValueError, TypeError, base64.binascii.Error) as e:
        logger.debug(f"Failed to decode base64 string: {e}")
        return None
    except UnicodeDecodeError as e:
        logger.warning(f"Could not decode bytes to UTF-8 after base64 decoding: {e}")
        return None
