#!/usr/bin/env python3
"""Local smoke-run: produce sample configs, fake metrics, and run the filter pipeline.
This doesn't perform real network tests; it's for CI/workflow validation.
"""
from pathlib import Path
import random
from src.config import Config
from src.filter import filter_and_rank
from src.network_metrics import Metrics


def generate_sample_configs(n=10):
    lines = []
    for i in range(n):
        proto = random.choice(['vmess', 'vless', 'trojan', 'shadowsocks'])
        lines.append(f"{proto}://sample-node-{i}@example.com:443")
    return lines


def generate_fake_metrics(raw):
    m = {}
    for r in raw:
        # simulate some successes and failures
        if random.random() < 0.6:
            metrics = Metrics(
                latency_ms=random.uniform(30, 400),
                jitter_ms=random.uniform(1, 20),
                packet_loss=random.uniform(0, 2),
                throughput_kbps=random.uniform(100, 5000),
                success=True,
            )
        else:
            metrics = Metrics(success=False)
        m[r] = metrics
    return m


def main():
    p = Path(Config.RAW_CONFIGS_PATH)
    raw = generate_sample_configs(20)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('\n'.join(raw), encoding='utf-8')
    metrics_map = generate_fake_metrics(raw)
    lines = filter_and_rank(raw, metrics_map)
    print(f"Smoke run produced {len(lines)} filtered nodes. Outputs written to {Config.OUTPUT_PLAIN_PATH} and {Config.OUTPUT_BASE64_PATH}")


if __name__ == '__main__':
    main()
