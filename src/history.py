from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from pathlib import Path
from typing import Dict, Deque

logger = logging.getLogger(__name__)

class NodeHistory:
    def __init__(self, max_size: int = 50):
        self.test_results: Deque[bool] = deque(maxlen=max_size)
        self.fail_count: int = 0

    def add_result(self, success: bool):
        if len(self.test_results) == self.test_results.maxlen and self.test_results[0] is False:
            self.fail_count = max(0, self.fail_count - 1)
        
        self.test_results.append(success)
        if not success:
            self.fail_count += 1

    @property
    def reliability(self) -> float:
        if not self.test_results:
            return 1.0  # Assume 100% reliable if no data
        return sum(1 for r in self.test_results if r) / len(self.test_results)
    
    def to_dict(self) -> dict:
        return {'results': list(self.test_results), 'fails': self.fail_count}

    @classmethod
    def from_dict(cls, data: dict) -> NodeHistory:
        history = cls(max_size=50)
        history.test_results.extend(data.get('results', []))
        history.fail_count = data.get('fails', 0)
        return history

class HistoryManager:
    """Manages the loading, updating, and saving of node historical data asynchronously."""
    def __init__(self, history_dir: Path, filename: str = "node_history.json"):
        self.history_file = history_dir / filename
        self.node_history: Dict[str, NodeHistory] = {}

    async def load_history(self):
        """Loads the history from a JSON file asynchronously."""
        if not self.history_file.exists():
            logger.info("History file not found. Starting with a clean slate.")
            return
        try:
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(None, self.history_file.read_text)
            data = await loop.run_in_executor(None, json.loads, content)
            self.node_history = {k: NodeHistory.from_dict(v) for k, v in data.items()}
            logger.info(f"Loaded history for {len(self.node_history)} nodes.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading history file: {e}. Starting fresh.")
            self.node_history = {}

    async def save_history(self):
        """Saves the history to a JSON file asynchronously."""
        try:
            loop = asyncio.get_running_loop()
            data = {k: v.to_dict() for k, v in self.node_history.items()}
            content = await loop.run_in_executor(None, lambda: json.dumps(data, indent=2))
            await loop.run_in_executor(None, self.history_file.write_text, content)
            logger.info(f"Successfully saved history for {len(self.node_history)} nodes.")
        except IOError as e:
            logger.error(f"Error saving history file: {e}")

    def update_node_history(self, node_id: str, success: bool):
        """Updates the history for a single node."""
        if node_id not in self.node_history:
            self.node_history[node_id] = NodeHistory()
        self.node_history[node_id].add_result(success)

    def get_reliability(self, node_id: str) -> float:
        return self.node_history.get(node_id, NodeHistory()).reliability

    def get_fail_count(self, node_id: str) -> int:
        return self.node_history.get(node_id, NodeHistory()).fail_count
