"""Configuration constants and helpers.

Defines file paths, timeouts, and other parameters used by the project.
The module ensures that a few essential directories exist on import so scripts can run
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
    """Static configuration for the project."""

    # Core binaries
    XRAY_BINARY: ClassVar[str] = str(BASE_DIR / "cores" / "xray")
    HIDDIFY_BINARY: ClassVar[str] = str(BASE_DIR / "cores" / "hiddify")

    # Input files
    SUBSCRIPTION_SOURCES_FILE: ClassVar[str] = str(BASE_DIR / "subscription_sources.txt")

    # Output files
    OUTPUT_DIR: ClassVar[str] = str(BASE_DIR / "output")
    OUTPUT_PLAIN_PATH: ClassVar[str] = str(OUTPUT_DIR / "merged_nodes.txt")
    OUTPUT_BASE64_PATH: ClassVar[str] = str(OUTPUT_DIR / "merged_sub_base64.txt")
    RAW_CONFIGS_PATH: ClassVar[str] = str(OUTPUT_DIR / "raw_configs.txt")

    # Workspace directories
    LOGS_DIR: ClassVar[str] = str(BASE_DIR / "logs")
    CACHE_DIR: ClassVar[str] = str(BASE_DIR / "cache")

    # Network timeouts (seconds)
    TCP_TIMEOUT: ClassVar[int] = 8
    HTTP_TIMEOUT: ClassVar[int] = 12
    DOWNLOAD_TIMEOUT: ClassVar[int] = 30

    # Filtering criteria
    MIN_THROUGHPUT_KBPS: ClassVar[int] = 50
    MAX_LATENCY_MS: ClassVar[int] = 2000

    # Supported protocols (used for pre-filtering)
    SUPPORTED_PROTOCOLS: ClassVar[List[str]] = [
        "vmess",
        "vless",
        "trojan",
        "shadowsocks",
        "ss",
        "hysteria",
    ]

    # Concurrency settings
    MAX_CONCURRENT_TESTS: ClassVar[int] = 50

    # Subscription sources - loaded on-demand
    _subscription_sources: ClassVar[List[str] | None] = None

    @classmethod
    def get_subscription_sources(cls) -> List[str]:
        """Loads and returns the list of subscription sources from the file."""
        if cls._subscription_sources is None:
            try:
                with open(cls.SUBSCRIPTION_SOURCES_FILE, "r", encoding="utf-8") as f:
                    sources = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                cls._subscription_sources = sources
            except FileNotFoundError:
                print(f"Warning: Subscription file not found at {cls.SUBSCRIPTION_SOURCES_FILE}. No sources to fetch.")
                cls._subscription_sources = []
        return cls._subscription_sources


def ensure_dirs() -> None:
    """Ensures that all necessary directories exist."""
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)


# Run once on import
ensure_dirs()
