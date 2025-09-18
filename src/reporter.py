"""Reporting helpers.

Small wrapper to post test results to an HTTP endpoint.
"""

from __future__ import annotations

import os
import json
from typing import List, Optional

import requests


def post_results(
    nodes: List[str], report_url: Optional[str] = None, api_key: Optional[str] = None
) -> dict:
    if not report_url:
        return {"status": "skipped", "reason": "no report_url"}
    payload = {"nodes": nodes, "meta": {"count": len(nodes)}}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    r = requests.post(report_url, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()
