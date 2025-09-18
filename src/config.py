
import os
import sys
from pathlib import Path

class Config:
    # Base Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / "output"
    CORES_DIR = BASE_DIR / "cores"
    CACHE_DIR = BASE_DIR / "cache"
    LOGS_DIR = BASE_DIR / "logs"
    CONFIGS_DIR = BASE_DIR / "configs"
    REPORTS_DIR = OUTPUT_DIR / "reports"
    STATS_DIR = OUTPUT_DIR / "stats"
    BACKUPS_DIR = OUTPUT_DIR / "backups"
    
    # Core Binaries
    XRAY_BINARY = str(CORES_DIR / "xray-core")
    HIDDIFY_BINARY = str(CORES_DIR / "hiddify-cli")
    
    # Network Timeouts (Optimized for minimal timeout)
    TCP_TIMEOUT = float(os.getenv("TCP_TIMEOUT", "3.0"))
    HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5.0"))
    DOWNLOAD_TIMEOUT = float(os.getenv("DOWNLOAD_TIMEOUT", "8.0"))
    STARTUP_DELAY = float(os.getenv("STARTUP_DELAY", "1.5"))
    CONNECTION_TIMEOUT = float(os.getenv("CONNECTION_TIMEOUT", "4.0"))
    SOCKS_TIMEOUT = float(os.getenv("SOCKS_TIMEOUT", "10.0"))
    GRPC_TIMEOUT = float(os.getenv("GRPC_TIMEOUT", "15.0"))
    QUIC_TIMEOUT = float(os.getenv("QUIC_TIMEOUT", "12.0"))
    
    # Performance Thresholds & Scoring Weights
    MIN_THROUGHPUT_KBPS = int(os.getenv("MIN_THROUGHPUT_KBPS", "100"))
    MAX_LATENCY_MS = int(os.getenv("MAX_LATENCY_MS", "1500"))
    MAX_JITTER_MS = int(os.getenv("MAX_JITTER_MS", "200"))
    MAX_PACKET_LOSS = float(os.getenv("MAX_PACKET_LOSS", "5.0"))
    MIN_SUCCESS_RATE = float(os.getenv("MIN_SUCCESS_RATE", "70.0"))  # %
    
    # Ideal values for normalization
    IDEAL_LATENCY_MS = int(os.getenv("IDEAL_LATENCY_MS", "50"))
    IDEAL_JITTER_MS = int(os.getenv("IDEAL_JITTER_MS", "10"))
    IDEAL_THROUGHPUT_KBPS = int(os.getenv("IDEAL_THROUGHPUT_KBPS", "10000")) # 10 MB/s
    IDEAL_PACKET_LOSS = float(os.getenv("IDEAL_PACKET_LOSS", "0"))

    # Metric weights for scoring
    LATENCY_WEIGHT = float(os.getenv("LATENCY_WEIGHT", "0.35"))
    JITTER_WEIGHT = float(os.getenv("JITTER_WEIGHT", "0.15"))
    THROUGHPUT_WEIGHT = float(os.getenv("THROUGHPUT_WEIGHT", "0.40"))
    RELIABILITY_WEIGHT = float(os.getenv("RELIABILITY_WEIGHT", "0.10"))
    PACKET_LOSS_WEIGHT = float(os.getenv("PACKET_LOSS_WEIGHT", "0.10"))
    
    # Concurrency Settings
    MAX_CONCURRENT_TESTS = int(os.getenv("MAX_CONCURRENT_TESTS", "50"))
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "20"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    SOCKS_RETRIES = int(os.getenv("SOCKS_RETRIES", "2"))
    BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "1.5"))
    
    # Test URLs (Multiple fallbacks with anti-ban rotation)
    SUBSCRIPTION_TEST_URL = os.getenv("SUBSCRIPTION_TEST_URL", "http://cp.cloudflare.com/")
    TEST_URLS = [
        "http://www.google.com/generate_204",
        "http://cp.cloudflare.com/",
        "http://detectportal.firefox.com/success.txt",
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://clients3.google.com/generate_204",
        "http://msftconnecttest.com/connecttest.txt",
    ]
    
    SPEED_TEST_URLS = [
        "https://raw.githubusercontent.com/v2fly/v2ray-core/master/LICENSE",
        "https://raw.githubusercontent.com/xtls/xray-core/main/LICENSE",
    ]
    
    # Subscription URLs
    SUBSCRIPTION_SOURCES = os.getenv("SUBSCRIPTION_SOURCES", "https://raw.githubusercontent.com/yebekhe/Config_V2ray/main/sub/mix").split(',')
    
    # Supported Protocols (All major protocols including XHTTP)
    SUPPORTED_PROTOCOLS = {
        "vmess", "vless", "trojan", "shadowsocks", "shadowsocksr",
        "hysteria", "hysteria2", "tuic", "naive", "brook",
        "wireguard", "xhttp", "xtls", "grpc", "websocket", "quic",
        "http", "socks", "ssh", "ping", "icmp", "dns"
    }
    
    # Advanced Protocol Settings
    PROTOCOL_SETTINGS = {
        "vmess": {"alterId": 0, "security": "auto"},
        "vless": {"flow": "", "encryption": "none"},
        "trojan": {"password": "", "network": "tcp"},
        "shadowsocks": {"method": "aes-256-gcm", "plugin": ""},
        "hysteria": {"protocol": "udp", "obfs": ""},
        "hysteria2": {"password": "", "obfs": ""},
        "tuic": {"uuid": "", "password": ""},
        "xhttp": {"path": "/", "headers": {}},
        "grpc": {"serviceName": "", "multiMode": False},
        "quic": {"security": "", "key": "", "header": {"type": "none"}},
    }
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
    
    # Cache Settings
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
    MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "1000000"))  # 1MB
    
    # Health Check Settings
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
    MAX_HEALTH_FAILURES = int(os.getenv("MAX_HEALTH_FAILURES", "3"))
    HEALTH_SERVER_PORT = int(os.getenv("HEALTH_SERVER_PORT", "8080"))
    
    # Output Settings
    OUTPUT_PLAIN_PATH = str(OUTPUT_DIR / "merged_nodes.txt")
    OUTPUT_BASE64_PATH = str(OUTPUT_DIR / "merged_sub_base64.txt")
    OUTPUT_REPORT_PATH = str(REPORTS_DIR / "report.json")
    OUTPUT_STATS_PATH = str(STATS_DIR / "stats.json")
    
    # Docker Settings
    DOCKER_NETWORK_MODE = os.getenv("DOCKER_NETWORK_MODE", "bridge")
    DOCKER_MEMORY_LIMIT = os.getenv("DOCKER_MEMORY_LIMIT", "2g")
    DOCKER_CPU_LIMIT = os.getenv("DOCKER_CPU_LIMIT", "2.0")
    
    # GitHub Actions Settings
    GITHUB_TIMEOUT_MINUTES = int(os.getenv("GITHUB_TIMEOUT_MINUTES", "30"))
    GITHUB_ARTIFACT_RETENTION = int(os.getenv("GITHUB_ARTIFACT_RETENTION", "7"))
    GITHUB_RUN_INTERVAL = int(os.getenv("GITHUB_RUN_INTERVAL", "60"))  # minutes
    
    # Advanced Optimization Flags
    ENABLE_MEMORY_OPTIMIZATION = os.getenv("ENABLE_MEMORY_OPTIMIZATION", "true").lower() == "true"
    ENABLE_NETWORK_OPTIMIZATION = os.getenv("ENABLE_NETWORK_OPTIMIZATION", "true").lower() == "true"
    ENABLE_CPU_OPTIMIZATION = os.getenv("ENABLE_CPU_OPTIMIZATION", "true").lower() == "true"
    ENABLE_CACHE_OPTIMIZATION = os.getenv("ENABLE_CACHE_OPTIMIZATION", "true").lower() == "true"
    ENABLE_SOCKS_OPTIMIZATION = os.getenv("ENABLE_SOCKS_OPTIMIZATION", "true").lower() == "true"
    ENABLE_GRPC_OPTIMIZATION = os.getenv("ENABLE_GRPC_OPTIMIZATION", "true").lower() == "true"
    ENABLE_QUIC_OPTIMIZATION = os.getenv("ENABLE_QUIC_OPTIMIZATION", "true").lower() == "true"
    
    # Security Settings
    ENABLE_SECURITY_CHECKS = os.getenv("ENABLE_SECURITY_CHECKS", "true").lower() == "true"
    MAX_CONFIG_SIZE = int(os.getenv("MAX_CONFIG_SIZE", "10000"))  # 10KB
    BLACKLISTED_IPS = {"127.0.0.1", "0.0.0.0", "255.255.255.255"}
    BLACKLISTED_DOMAINS = {"localhost", "example.com", "test.com"}
    ENABLE_ANTI_BAN = os.getenv("ENABLE_ANTI_BAN", "true").lower() == "true"
    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.1"))  # seconds
    RANDOMIZE_REQUESTS = os.getenv("RANDOMIZE_REQUESTS", "true").lower() == "true"
    
    # Monitoring Settings
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
    METRICS_UPDATE_INTERVAL = int(os.getenv("METRICS_UPDATE_INTERVAL", "10"))
    ENABLE_PROMETHEUS = os.getenv("ENABLE_PROMETHEUS", "true").lower() == "true"
    
    # Advanced Features
    ENABLE_AUTO_UPDATE = os.getenv("ENABLE_AUTO_UPDATE", "true").lower() == "true"
    ENABLE_BACKUP = os.getenv("ENABLE_BACKUP", "true").lower() == "true"
    ENABLE_ALERTING = os.getenv("ENABLE_ALERTING", "true").lower() == "true"
    ENABLE_PERFORMANCE_MONITORING = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    
    @classmethod
    def get_subscription_sources(cls) -> list[str]:
        return [src.strip() for src in cls.SUBSCRIPTION_SOURCES if src.strip()]

    @classmethod
    def setup_directories(cls):
        """Create all necessary directories if they don't exist."""
        for dir_path in [cls.OUTPUT_DIR, cls.CORES_DIR, cls.CACHE_DIR, cls.LOGS_DIR, 
                        cls.REPORTS_DIR, cls.STATS_DIR, cls.BACKUPS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

# Initialize and validate the configuration at import time
try:
    Config.setup_directories()
except Exception as e:
    print(f"❌ Error setting up directories: {e}", file=sys.stderr)
    sys.exit(1)
