"""Collection of UNO agent strategies."""

from .monte_carlo import monte_carlo_agent
from .priority_queue import priority_queue_agent
from .iddfs import iddfs_agent

__all__ = ["monte_carlo_agent", "priority_queue_agent", "iddfs_agent"]

