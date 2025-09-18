"""Parsers for various proxy configuration URI schemes.

This module provides functions to deconstruct different proxy configuration links
(e.g., vmess://) into a structured format that can be used to generate Xray/V2Ray
configuration files.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse, unquote, parse_qs

logger = logging.getLogger(__name__)

def parse_vmess_uri(uri: str) -> Optional[Dict[str, Any]]:
    """Parses a vmess:// URI and returns an Xray outbound configuration dictionary."""
    try:
        if not uri.startswith("vmess://"):
            return None

        decoded_part = base64.b64decode(uri[8:]).decode('utf-8')
        vmess_data = json.loads(decoded_part)

        # Basic fields
        outbound = {
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": vmess_data.get("add"),
                        "port": int(vmess_data.get("port")),
                        "users": [
                            {
                                "id": vmess_data.get("id"),
                                "alterId": int(vmess_data.get("aid")),
                                "security": vmess_data.get("scy", "auto"),
                            }
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": vmess_data.get("net", "tcp"),
                "security": vmess_data.get("tls", ""),
            },
            "mux": {"enabled": True, "concurrency": 8}
        }

        # Stream settings
        net = vmess_data.get("net", "tcp")
        stream_settings = outbound["streamSettings"]
        if net == "tcp":
            stream_settings["tcpSettings"] = {"header": {"type": vmess_data.get("type", "none")}}
        elif net == "kcp":
            stream_settings["kcpSettings"] = {"header": {"type": vmess_data.get("type", "none")}}
        elif net == "ws":
            stream_settings["wsSettings"] = {"path": vmess_data.get("path", "/"), "headers": {"Host": vmess_data.get("host", "")}}
        elif net == "h2":
            stream_settings["httpSettings"] = {"path": vmess_data.get("path", "/"), "host": vmess_data.get("host", "")}
        elif net == "grpc":
            stream_settings["grpcSettings"] = {"serviceName": vmess_data.get("path", "")}

        # TLS settings
        if vmess_data.get("tls") == "tls":
            stream_settings["tlsSettings"] = {
                "serverName": vmess_data.get("sni", vmess_data.get("host", "")),
                "allowInsecure": True,
            }
        
        return outbound

    except (json.JSONDecodeError, base64.binascii.Error, KeyError, TypeError) as e:
        logger.warning(f"Could not parse vmess URI: {e}")
        return None

def parse_v2ray_uri(uri: str) -> Optional[Dict[str, Any]]:
    """Generic parser that delegates to protocol-specific parsers."""
    if uri.startswith("vmess://"):
        return parse_vmess_uri(uri)
    # Add other protocols here, e.g.:
    # elif uri.startswith("ss://"):
    #     return parse_ss_uri(uri)
    else:
        logger.debug(f"Unsupported URI scheme for: {uri[:40]}...")
        return None
