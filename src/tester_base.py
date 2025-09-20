"""Defines the abstract base class for all node testers.

This module provides the `NodeTester` ABC, which establishes a common interface
for any class that aims to test the network performance of a proxy configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .xray_tester import PortManager

from .config import Config
from .models import Node, NodeMetrics


class NodeTester(ABC):
    """Abstract Base Class for a proxy node tester.

    All concrete tester implementations (e.g., for Xray, Hiddify) should inherit
    from this class and implement its abstract methods.
    """

    @abstractmethod
    def __init__(self, config: Config, port_manager: "PortManager") -> None:
        pass

    @abstractmethod
    async def test_node(self, node: Node) -> Optional[NodeMetrics]:
        """Tests a single proxy configuration and returns its network metrics.

        Args:
            node: The `Node` object to be tested.

        Returns:
            A `NodeMetrics` object containing the performance data if the test is successful,
            or `None` if the test fails, is inconclusive, or the node is invalid.
        """
        pass

    @abstractmethod
    async def __aenter__(self):
        """Asynchronous context manager entry.

        This method should handle any setup required by the tester, such as verifying
        the existence of a binary or initializing resources.
        It should return `self`.
        """
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Asynchronous context manager exit.

        This method should handle the cleanup of any resources used by the tester.
        """
        pass
