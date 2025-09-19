from __future__ import annotations

import os
from pathlib import Path
from typing import List

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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
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
    TESTER: str = Field("xray", env="TESTER")  # Can be 'xray' or 'hiddify'
    RUN_INTERVAL_MINUTES: int = Field(60, env="RUN_INTERVAL_MINUTES")

    # --- Network Settings ---
    HTTP_TIMEOUT: float = Field(8.0, env="HTTP_TIMEOUT")
    LATENCY_TEST_URL: str = Field("http://cp.cloudflare.com/", env="LATENCY_TEST_URL")
    SPEED_TEST_URL: str = Field("https://raw.githubusercontent.com/v2fly/v2ray-core/master/LICENSE", env="SPEED_TEST_URL")

    # --- Tester Configuration ---
    MAX_CONCURRENT_TESTS: int = Field(50, env="MAX_CONCURRENT_TESTS")
    XRAY_SOCKS_PORT_START: int = Field(20000, env="XRAY_SOCKS_PORT_START")
    XRAY_SOCKS_PORT_END: int = Field(21000, env="XRAY_SOCKS_PORT_END")

    # --- Subscription Sources ---
    SUBSCRIPTION_SOURCES: List[str] = Field(
        default=["https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_base64.txt"],
        env="SUBSCRIPTION_SOURCES",
    )

    # --- Filtering Criteria ---
    MAX_LATENCY_MS: int = Field(2000, env="MAX_LATENCY_MS")
    MIN_THROUGHPUT_KBPS: float = Field(100.0, env="MIN_THROUGHPUT_KBPS")
    MAX_HISTORIC_FAIL_COUNT: int = Field(5, env="MAX_HISTORIC_FAIL_COUNT")
    MIN_RELIABILITY: float = Field(0.75, env="MIN_RELIABILITY", ge=0.0, le=1.0)

    # --- Health & Logging ---
    HEALTH_CHECK_PORT: int = Field(8080, env="HEALTH_CHECK_PORT")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

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
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("SKIP_BINARY_CHECKS"):
            logger.debug("Skipping binary existence/executable checks (test or SKIP_BINARY_CHECKS set)")
            return self

        # Validate the chosen tester's binary
        if self.TESTER == "xray":
            binary_path = self.XRAY_BINARY
        elif self.TESTER == "hiddify":
            binary_path = self.HIDDIFY_BINARY
        else:
            raise ValueError(f"Invalid tester specified: '{self.TESTER}'. Must be 'xray' or 'hiddify'.")

        if not isinstance(binary_path, Path) or not binary_path.is_file():
            raise FileNotFoundError(f"Required binary for tester '{self.TESTER}' not found at: {binary_path}")
        if not os.access(binary_path, os.X_OK):
            raise PermissionError(f"Binary for tester '{self.TESTER}' is not executable: {binary_path}")

        return self

        model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

# Instantiate the config to be used globally
try:
    config = Config()
except Exception as e:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Configuration validation failed: {e}")
    exit(1)
