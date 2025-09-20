
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from src.history import NodeHistory, HistoryManager


class TestNodeHistory:
    def test_initial_state(self):
        history = NodeHistory()
        assert history.reliability == 1.0
        assert history.fail_count == 0
        assert len(history.test_results) == 0

    def test_add_success(self):
        history = NodeHistory()
        history.add_result(True)
        assert history.reliability == 1.0
        assert history.fail_count == 0

    def test_add_failure(self):
        history = NodeHistory()
        history.add_result(False)
        assert history.reliability == 0.0
        assert history.fail_count == 1

    def test_reliability_calculation(self):
        history = NodeHistory()
        history.add_result(True)
        history.add_result(True)
        history.add_result(False)
        history.add_result(True)
        assert history.reliability == 0.75

    def test_rolling_window(self):
        history = NodeHistory(max_size=3)
        history.add_result(False) # fail_count = 1
        history.add_result(True)
        history.add_result(True)
        assert history.fail_count == 1
        history.add_result(True) # This should push out the first False result
        assert history.fail_count == 0 # The fail should have been rolled out
        assert list(history.test_results) == [True, True, True]

    def test_to_from_dict(self):
        history = NodeHistory()
        history.add_result(True)
        history.add_result(False)
        data = history.to_dict()
        new_history = NodeHistory.from_dict(data)
        assert new_history.reliability == 0.5
        assert new_history.fail_count == 1


class TestHistoryManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return HistoryManager(history_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_load_history_not_found(self, manager):
        await manager.load_history()
        assert manager.node_history == {}

    @pytest.mark.asyncio
    async def test_save_and_load_history(self, manager):
        manager.update_node_history("node1", True)
        manager.update_node_history("node1", False)
        await manager.save_history()

        new_manager = HistoryManager(history_dir=manager.history_file.parent)
        await new_manager.load_history()

        assert "node1" in new_manager.node_history
        assert new_manager.get_reliability("node1") == 0.5
        assert new_manager.get_fail_count("node1") == 1

    @pytest.mark.asyncio
    async def test_load_history_bad_json(self, manager):
        manager.history_file.write_text("bad json")
        await manager.load_history()
        assert manager.node_history == {}

    def test_update_and_get(self, manager):
        assert manager.get_reliability("node2") == 1.0 # Default reliability
        assert manager.get_fail_count("node2") == 0

        manager.update_node_history("node2", False)
        assert manager.get_reliability("node2") == 0.0
        assert manager.get_fail_count("node2") == 1
