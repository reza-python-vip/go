from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import logging

# Support both pydantic v1 and v2, and handle environments where
# `pydantic-settings` is not installed (pydantic v2 split).
import pydantic as _pydantic

PydanticV2 = _pydantic.__version__.split(".")[0] == "2"

if PydanticV2:
    # Try to use the proper settings class from pydantic-settings
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
        from pydantic import Field
        from pydantic import field_validator, model_validator
    except ImportError:
        # pydantic v2 present but pydantic-settings not installed. Fall back to
        # BaseModel to avoid import-time failures; validators are no-ops.
        from pydantic import BaseModel as BaseSettings, Field

        def field_validator(*args, **kwargs):  # type: ignore
            def _decor(fn):
                return fn

            return _decor

        def model_validator(*args, **kwargs):  # type: ignore
            def _decor(fn):
                return fn

            return _decor

        class SettingsConfigDict(dict):  # type: ignore
            pass
else:
    # pydantic v1
    from pydantic import BaseSettings, Field, root_validator, validator

    field_validator = validator  # type: ignore
    model_validator = root_validator  # type: ignore

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Application configuration with validation."""

    # Network settings
    XRAY_SOCKS_PORT_START: int = Field(default=10000, gt=1024, lt=65535)
    XRAY_SOCKS_PORT_END: int = Field(default=20000, gt=1024, lt=65535)
    HTTP_TIMEOUT: float = Field(default=5.0, gt=0)
    TCP_TIMEOUT: float = Field(default=3.0, gt=0)
    CONNECTION_TIMEOUT: float = Field(default=4.0, gt=0)
    DOWNLOAD_TIMEOUT: float = Field(default=8.0, gt=0)

    # File paths
    XRAY_BINARY: Path = Field(default=Path("xray"))
    CONFIG_FILE: Path = Field(default=Path("config.yml"))
    TEMP_DIR: Path = Field(default_factory=lambda: Path(tempfile.gettempdir()))
    OUTPUT_DIR: Path = Field(default=Path("output"))

    # Test settings
    LATENCY_TEST_URL: str = Field(default="http://www.gstatic.com/generate_204")
    STRICT: bool = Field(default=True)
    KEEP_ALIVE: bool = Field(default=False)
    HISTORY_FILE: Path = Field(default=Path("history.json"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("XRAY_SOCKS_PORT_END")
    def validate_port_range(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate that port range is valid."""
        start = values.get("XRAY_SOCKS_PORT_START", 10000)
        if v <= start:
            raise ValueError(
                f"XRAY_SOCKS_PORT_END ({v}) must be greater than XRAY_SOCKS_PORT_START ({start})"
            )
        return v

    @field_validator("XRAY_BINARY", "TEMP_DIR", "OUTPUT_DIR")
    def validate_directories(cls, v: Path) -> Path:
        """Validate that directories exist and are accessible."""
        if not v.parent.exists():
            try:
                v.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Could not create directory {v.parent}: {e}")
        return v

    @field_validator("LATENCY_TEST_URL")
    def validate_url(cls, v: str) -> str:
        """Validate that URL is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("LATENCY_TEST_URL must start with http:// or https://")
        return v

    @model_validator
    def validate_timeouts(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that timeouts are properly configured."""
        http_timeout = values.get("HTTP_TIMEOUT", 5.0)
        tcp_timeout = values.get("TCP_TIMEOUT", 3.0)
        connection_timeout = values.get("CONNECTION_TIMEOUT", 4.0)
        download_timeout = values.get("DOWNLOAD_TIMEOUT", 8.0)

        # Connection timeout should be greater than TCP timeout
        if connection_timeout <= tcp_timeout:
            raise ValueError(
                f"CONNECTION_TIMEOUT ({connection_timeout}) must be greater than TCP_TIMEOUT ({tcp_timeout})"
            )

        # Download timeout should be greater than HTTP timeout
        if download_timeout <= http_timeout:
            raise ValueError(
                f"DOWNLOAD_TIMEOUT ({download_timeout}) must be greater than HTTP_TIMEOUT ({http_timeout})"
            )

        return values

    def get_metrics_config(self) -> Dict[str, float]:
        """Get configuration for metrics collection."""
        return {
            "http_timeout": self.HTTP_TIMEOUT,
            "tcp_timeout": self.TCP_TIMEOUT,
            "connection_timeout": self.CONNECTION_TIMEOUT,
            "download_timeout": self.DOWNLOAD_TIMEOUT,
        }

    # --- Core Paths ---
    BASE_DIR: Path = Path(__file__).parent.parent.resolve()
    LOGS_DIR: Path = BASE_DIR / "logs"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    TEMP_DIR: Path = BASE_DIR / "temp"
    CORES_DIR: Path = BASE_DIR / "cores"

    # --- Binaries ---
    XRAY_BINARY: Path = CORES_DIR / "xray"
    HIDDIFY_BINARY: Path = CORES_DIR / "hiddify"

    # --- Run Control ---
    TESTER: str = Field("xray", validation_alias="TESTER")  # Can be 'xray' or 'hiddify'
    RUN_INTERVAL_MINUTES: int = Field(60, validation_alias="RUN_INTERVAL_MINUTES")

    # --- Network Settings ---
    HTTP_TIMEOUT: float = Field(8.0, validation_alias="HTTP_TIMEOUT")
    LATENCY_TEST_URL: str = Field(
        "http://cp.cloudflare.com/", validation_alias="LATENCY_TEST_URL"
    )
    SPEED_TEST_URL: str = Field(
        "https://raw.githubusercontent.com/v2fly/v2ray-core/master/LICENSE",
        validation_alias="SPEED_TEST_URL",
    )

    # --- Tester Configuration ---
    MAX_CONCURRENT_TESTS: int = Field(50, validation_alias="MAX_CONCURRENT_TESTS")
    XRAY_SOCKS_PORT_START: int = Field(20000, validation_alias="XRAY_SOCKS_PORT_START")
    XRAY_SOCKS_PORT_END: int = Field(21000, validation_alias="XRAY_SOCKS_PORT_END")

    # --- Subscription Sources ---
    SUBSCRIPTION_SOURCES: List[str] = Field(
        default=[
            "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_base64.txt"
        ],
        validation_alias="SUBSCRIPTION_SOURCES",
    )

    # --- Filtering Criteria ---
    MAX_LATENCY_MS: int = Field(2000, validation_alias="MAX_LATENCY_MS")
    MIN_THROUGHPUT_KBPS: float = Field(100.0, validation_alias="MIN_THROUGHPUT_KBPS")
    MAX_HISTORIC_FAIL_COUNT: int = Field(5, validation_alias="MAX_HISTORIC_FAIL_COUNT")
    MIN_RELIABILITY: float = Field(
        0.75, validation_alias="MIN_RELIABILITY", ge=0.0, le=1.0
    )

    # --- Health & Logging ---
    HEALTH_CHECK_PORT: int = Field(8080, validation_alias="HEALTH_CHECK_PORT")
    LOG_LEVEL: str = Field("INFO", validation_alias="LOG_LEVEL")

    # --- Output Files ---
    @property
    def OUTPUT_SUBSCRIPTION_PATH(self) -> str:
        return str(self.OUTPUT_DIR / "subscription.txt")

    @property
    def OUTPUT_REPORT_PATH(self) -> str:
        return str(self.OUTPUT_DIR / "report.md")

    # Create required directories and (optionally) validate tester binaries.
    # During test collection (pytest) we skip binary existence/executable checks
    # to avoid failing imports in environments that don't have the binaries.
    @model_validator(mode="after")
    def _validate_and_create_dirs(self) -> "Config":
        # Create all directories
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.CORES_DIR.mkdir(parents=True, exist_ok=True)

        # If running under pytest or if explicitly disabled, skip binary checks
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get(
            "SKIP_BINARY_CHECKS"
        ):
            logger.debug(
                "Skipping binary existence/executable checks (test or SKIP_BINARY_CHECKS set)"
            )
            return self

        # Validate the chosen tester's binary
        if self.TESTER == "xray":
            binary_path = self.XRAY_BINARY
        elif self.TESTER == "hiddify":
            binary_path = self.HIDDIFY_BINARY
        else:
            raise ValueError(
                f"Invalid tester specified: '{self.TESTER}'. Must be 'xray' or 'hiddify'."
            )

        if not isinstance(binary_path, Path) or not binary_path.is_file():
            raise FileNotFoundError(
                f"Required binary for tester '{self.TESTER}' not found at: {binary_path}"
            )
        if not os.access(binary_path, os.X_OK):
            raise PermissionError(
                f"Binary for tester '{self.TESTER}' is not executable: {binary_path}"
            )

        return self


# Instantiate the config to be used globally
try:
    config = Config()
except Exception as e:
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Configuration validation failed: {e}")
    exit(1)
