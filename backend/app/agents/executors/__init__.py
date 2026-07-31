"""Import every platform executor so its `register_executor` call runs, then
expose the registry lookup used by the execution engine.
"""
from app.agents.executors.base import Executor, get_executor_class, register_executor
from app.agents.executors.web.playwright_executor import WebExecutor

register_executor("web", WebExecutor)

__all__ = ["Executor", "get_executor_class", "register_executor", "WebExecutor"]
