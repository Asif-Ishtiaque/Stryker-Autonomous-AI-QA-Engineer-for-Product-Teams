import pytest

from app.agents.executors.base import get_executor_class, register_executor
from app.agents.executors.web.playwright_executor import WebExecutor


def test_web_executor_is_registered_by_importing_executors_package():
    import app.agents.executors  # noqa: F401 — triggers registration side effect

    assert get_executor_class("web") is WebExecutor


def test_unregistered_platform_raises_with_helpful_message():
    with pytest.raises(ValueError, match="No executor registered"):
        get_executor_class("holodeck")


def test_register_executor_is_a_pure_extension_point():
    class FakeExecutor(WebExecutor):
        platform = "fake"

    register_executor("fake", FakeExecutor)
    assert get_executor_class("fake") is FakeExecutor
