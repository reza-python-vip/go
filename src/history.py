"""Manages the historical performance data of proxy nodes.

This module provides the `HistoryManager` class, which is responsible for
loading, updating, and saving the test history of nodes. This allows for
the calculation of reliability scores over time.
"""

import json
import logging
from collections import deque
from pathlib import Path
from typing import Dict, Deque

from .config import Config

# Define a simple structure for a node's history
class NodeHistory:
    def __init__(self, max_size: int = 50):
        self.test_results: Deque[bool] = deque(maxlen=max_size)
        self.success_count = 0
        self.total_tests = 0

    def add_test_result(self, success: bool):
        """Adds a new test result and updates counts."""
        if len(self.test_results) == self.test_results.maxlen:
            # If the deque is full, the oldest item is automatically evicted.
            # We need to adjust the success_count manually.
            if self.test_results[0]:
                self.success_count -= 1
        
        self.test_results.append(success)
        if success:
            self.success_count += 1
        self.total_tests = len(self.test_results)

    @property
    def reliability(self) -> float:
        """Calculates the reliability as the ratio of successful tests."""
        if not self.total_tests:
            return 1.0  # Assume reliable until proven otherwise
        return self.success_count / self.total_tests

    def to_dict(self) -> Dict:
        return {
            'test_results': list(self.test_results),
            'success_count': self.success_count,
            'total_tests': self.total_tests
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'NodeHistory':
        history = cls(max_size=data.get('max_size', 50))
        history.test_results.extend(data.get('test_results', []))
        history.success_count = data.get('success_count', 0)
        history.total_tests = data.get('total_tests', 0)
        return history

class HistoryManager:
    """Manages the loading, updating, and saving of node historical data."""
    def __init__(self, history_file: Path = Config.OUTPUT_DIR / 'node_history.json'):
        self.history_file = history_file
        self.node_history: Dict[str, NodeHistory] = {}

    def load_history(self):
        """Loads the history from a JSON file."""
        if not self.history_file.exists():
            logging.info("History file not found. Starting with a clean slate.")
            return
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                self.node_history = {k: NodeHistory.from_dict(v) for k, v in data.items()}
            logging.info(f"Loaded history for {len(self.node_history)} nodes.")
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading history file: {e}. Starting fresh.")
            self.node_history = {}

    def save_history(self):
        """Saves the history to a JSON file."""
        try:
            with open(self.history_file, 'w') as f:
                data = {k: v.to_dict() for k, v in self.node_history.items()}
                json.dump(data, f, indent=4)
            logging.info(f"Successfully saved history for {len(self.node_history)} nodes.")
        except IOError as e:
            logging.error(f"Error saving history file: {e}")

    def update_node_history(self, node_id: str, success: bool):
        """Updates the history for a single node."""
        if node_id not in self.node_history:
            self.node_history[node_id] = NodeHistory()
        self.node_history[node_id].add_test_result(success)

    def get_reliability(self, node_id: str) -> float:
        """Gets the reliability score for a given node."""
        if node_id not in self.node_history:
            return 1.0  # Default for new nodes
        return self.node_history[node_id].reliability
