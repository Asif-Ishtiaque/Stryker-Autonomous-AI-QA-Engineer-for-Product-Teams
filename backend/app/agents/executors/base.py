"""Plugin interface every platform executor (web, REST API, mobile, desktop)
must implement. The PlannerAgent emits platform-agnostic PlannedSteps; a
registered Executor is the only thing that knows how to actually perform a
step against its platform and report back evidence.

Registering a new platform (e.g. GraphQL, or a native mobile driver) means
writing one class and calling `register_executor` — nothing in the planner,
validator, or execution engine needs to change. This is the extensibility
seam the PRD requires for "future plugins."
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.state import ExecutedStepResult, PlannedStep
from app.llm.base import LLMProvider

StepEventSink = Callable[[dict[str, Any]], Awaitable[None]]


class Executor(ABC):
    """One instance is created per Run, used for every step in that run's plan.

    Every executor receives an LLMProvider, not just a browser/API client —
    self-healing and vision/semantic disambiguation are cross-platform
    concerns (a renamed button breaks web, a renamed control breaks desktop
    accessibility APIs the same way), so the reasoning fallback lives per
    platform but the model access point is standardized here.
    """

    platform: str

    def __init__(
        self,
        base_url: str,
        credential: dict[str, Any] | None,
        on_event: StepEventSink,
        llm: LLMProvider,
        run_id: uuid.UUID | None = None,
    ) -> None:
        self.base_url = base_url
        self.credential = credential
        self.on_event = on_event
        self.llm = llm
        # Optional: only the web executor uses this today, to key its CDP
        # screencast's Redis channel (see app.agents.executors.web.screencast).
        # Other platforms can ignore it.
        self.run_id = run_id

    @abstractmethod
    async def setup(self) -> None:
        """Acquire whatever session/session state the platform needs (browser
        context, API client, device connection, ...)."""

    @abstractmethod
    async def execute_step(self, step: PlannedStep) -> ExecutedStepResult:
        ...

    @abstractmethod
    async def teardown(self) -> None:
        """Release resources back to any pool; must not raise."""


_REGISTRY: dict[str, type[Executor]] = {}


def register_executor(platform: str, cls: type[Executor]) -> None:
    _REGISTRY[platform] = cls


def get_executor_class(platform: str) -> type[Executor]:
    try:
        return _REGISTRY[platform]
    except KeyError as exc:
        raise ValueError(
            f"No executor registered for platform '{platform}'. "
            f"Registered: {sorted(_REGISTRY)}"
        ) from exc
