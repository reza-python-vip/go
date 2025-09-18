import asyncio
from dataclasses import dataclass
from typing import Optional, Dict
import time


@dataclass
class Metrics:
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss: Optional[float] = None
    throughput_kbps: Optional[float] = None
    success: bool = False


class MetricsAnalyzer:
    @staticmethod
    def score(m: Metrics) -> float:
        if not m or not m.success:
            return 0.0
        score = 100.0
        if m.latency_ms:
            score -= min(80.0, m.latency_ms / 10.0)
        if m.throughput_kbps:
            score += min(50.0, m.throughput_kbps / 50.0)
        if m.packet_loss:
            score -= min(50.0, m.packet_loss * 2)
        return max(0.0, score)


async def measure_throughput(proxy: str, target: str = 'https://www.google.com') -> Metrics:
    # Lightweight throughput probe using aiohttp
    import aiohttp
    m = Metrics()
    try:
        t0 = time.time()
        async with aiohttp.ClientSession() as s:
            async with s.get(target, timeout=10) as r:
                _ = await r.content.read(1024)
        t1 = time.time()
        m.success = True
        m.latency_ms = (t1 - t0) * 1000.0
        m.throughput_kbps = max(1.0, 1024.0 / (t1 - t0))
    except Exception:
        m.success = False
    return m
