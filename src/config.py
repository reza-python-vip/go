from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import BaseSettings, Field, root_validator, validator


class Config(BaseSettings):
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

    # --- Validators ---
    @validator("SUBSCRIPTION_SOURCES", pre=True)
    def _split_str_to_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @root_validator(skip_on_failure=True)
    def _validate_binaries_and_dirs(cls, values):
        # Create all directories
        for key, value in values.items():
            if isinstance(value, Path) and key.endswith("_DIR"):
                value.mkdir(parents=True, exist_ok=True)
        
        # Validate the chosen tester's binary
        tester = values.get("TESTER").lower()
        if tester == "xray":
            binary_path = values.get("XRAY_BINARY")
        elif tester == "hiddify":
            binary_path = values.get("HIDDIFY_BINARY")
        else:
            raise ValueError(f"Invalid tester specified: '{values.get('TESTER')}'. Must be 'xray' or 'hiddify'.")

        if not binary_path.is_file():
            raise FileNotFoundError(f"Required binary for tester '{tester}' not found at: {binary_path}")
        if not os.access(binary_path, os.X_OK):
            raise PermissionError(f"Binary for tester '{tester}' is not executable: {binary_path}")
            
        return values

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instantiate the config to be used globally
try:
    config = Config()
except Exception as e:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Configuration validation failed: {e}")
    exit(1)
