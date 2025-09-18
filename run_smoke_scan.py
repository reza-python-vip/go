#!/usr/bin/env python3
"""Local smoke-run: produce sample configs, fake metrics, and run the filter pipeline.
This doesn't perform real network tests; it's for CI/workflow validation.
"""
import argparse
from pathlib import Path
import random
from src.config import Config
from src.filter import filter_and_rank
from src.network_metrics import Metrics

# More diverse and realistic-looking sample data
PROTOCOLS = ['vmess', 'vless', 'trojan', 'shadowsocks', 'ss']
DOMAINS = ['example.com', 'test-cdn.net', 'my-proxy.org', 'cloudflare.com']
USER_IDS = [
    'a1b2c3d4-e5f6-7890-1234-567890abcdef',
    'b2c3d4e5-f6a7-8901-2345-67890abcdef1',
    'c3d4e5f6-a7b8-9012-3456-7890abcdef12',
]

def generate_sample_configs(n: int = 10) -> list[str]:
    """Generates a list of n sample proxy configuration lines."""
    lines = []
    for i in range(n):
        proto = random.choice(PROTOCOLS)
        user = random.choice(USER_IDS)
        domain = random.choice(DOMAINS)
        port = random.choice([443, 8443, 2053, 2083, 2087])
        # Add some variation to the format
        if proto in ['vmess', 'vless']:
            lines.append(f"{proto}://{user}@{domain}:{port}?path=%2F&security=tls&sni={domain}&type=ws#{domain}-sample-{i}")
        elif proto in ['trojan', 'ss']:
            lines.append(f"{proto}://{user}@{domain}:{port}#{domain}-sample-{i}")
        else:
            lines.append(f"{proto}://{user}@{domain}:{port}#{domain}-sample-{i}")
    return lines


def generate_fake_metrics(raw_configs: list[str]) -> dict[str, Metrics]:
    """Generates a map of fake metrics for the given raw configs."""
    metrics_map = {}
    for config_line in raw_configs:
        # Make metrics slightly less random: good domains have better stats
        is_good_domain = any(d in config_line for d in ['cloudflare.com', 'test-cdn.net'])
        success_chance = 0.8 if is_good_domain else 0.5

        if random.random() < success_chance:
            # Successful connection
            latency = random.uniform(30, 250) if is_good_domain else random.uniform(150, 800)
            metrics = Metrics(
                latency_ms=latency,
                jitter_ms=random.uniform(1, latency / 10),
                packet_loss=random.uniform(0, 1) if is_good_domain else random.uniform(0, 5),
                throughput_kbps=random.uniform(2000, 10000) if is_good_domain else random.uniform(100, 2000),
                success=True,
            )
        else:
            # Failed connection
            metrics = Metrics(success=False)
        
        metrics_map[config_line] = metrics
    return metrics_map


def main():
    """Main function to run the smoke test."""
    parser = argparse.ArgumentParser(description="Run a smoke test for the proxy filter pipeline.")
    parser.add_argument(
        "-n", "--nodes",
        type=int,
        default=50,
        help="Number of sample nodes to generate."
    )
    args = parser.parse_args()

    print(f"[SmokeRun] Generating {args.nodes} sample configuration lines...")
    raw_configs = generate_sample_configs(args.nodes)
    
    config_path = Path(Config.RAW_CONFIGS_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('\n'.join(raw_configs), encoding='utf-8')
    print(f"[SmokeRun] Wrote sample configs to {config_path}")

    print("[SmokeRun] Generating fake metrics for sample configs...")
    metrics_map = generate_fake_metrics(raw_configs)

    print("[SmokeRun] Filtering and ranking nodes...")
    filtered_lines = filter_and_rank(raw_configs, metrics_map)
    
    # The filter_and_rank function already writes the output, so we just report on it.
    print(f"[SmokeRun] Completed. Produced {len(filtered_lines)} filtered nodes.")
    print(f"   - Plain text output: {Config.OUTPUT_PLAIN_PATH}")
    print(f"   - Base64 output: {Config.OUTPUT_BASE64_PATH}")


if __name__ == '__main__':
    main()
