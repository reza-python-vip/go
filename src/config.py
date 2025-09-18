"""Configuration constants and helpers.

Defines file paths and timeouts used by the project. The module ensures
that a few essential directories exist on import so scripts can run
without extra setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import ClassVar, List


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    XRAY_BINARY: ClassVar[str] = str(BASE_DIR / "cores" / "xray")
    HIDDIFY_BINARY: ClassVar[str] = str(BASE_DIR / "cores" / "hiddify")
    OUTPUT_PLAIN_PATH: ClassVar[str] = str(BASE_DIR / "output" / "merged_nodes.txt")
    OUTPUT_BASE64_PATH: ClassVar[str] = str(BASE_DIR / "output" / "merged_sub_base64.txt")
    RAW_CONFIGS_PATH: ClassVar[str] = str(BASE_DIR / "output" / "raw_configs.txt")
    LOGS_DIR: ClassVar[str] = str(BASE_DIR / "logs")
    CACHE_DIR: ClassVar[str] = str(BASE_DIR / "cache")
    TCP_TIMEOUT: ClassVar[int] = 8
    HTTP_TIMEOUT: ClassVar[int] = 12
    DOWNLOAD_TIMEOUT: ClassVar[int] = 30
    MIN_THROUGHPUT_KBPS: ClassVar[int] = 50
    MAX_LATENCY_MS: ClassVar[int] = 2000
    SUPPORTED_PROTOCOLS: ClassVar[List[str]] = [
        "vmess",
        "vless",
        "trojan",
        "shadowsocks",
        "hysteria",
    ]


def ensure_dirs() -> None:
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(Config.OUTPUT_PLAIN_PATH), exist_ok=True)


ensure_dirs()
