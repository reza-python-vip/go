"""Generates subscription output formats.

This module handles the creation of plain-text and base64-encoded subscription files
from a list of filtered and ranked proxy configurations.
"""

from __future__ import annotations

import base64
from typing import List, Tuple


def_encode_to_base64_sub(configs: List[str]) -> str:
    """Takes a list of config lines and returns a single base64-encoded string."""
    if not configs:
        return ""
    # Join all configs with a newline, encode to bytes, then to base64
    combined_text = "\n".join(configs)
    return base64.b64encode(combined_text.encode("utf-8")).decode("utf-8")


def generate_subscription_links(filtered_configs: List[str]) -> Tuple[str, str]:
    """Generates both plain-text and base64-encoded subscription content.

    Args:
        filtered_configs: A list of final, ranked configuration strings.

    Returns:
        A tuple containing:
        - The plain-text subscription content (nodes joined by newlines).
        - The base64-encoded subscription content.
    """
    plain_text_sub = "\n".join(filtered_configs)
    base64_sub = _encode_to_base64_sub(filtered_configs)
    
    return plain_text_sub, base64_sub
