"""Shared state threaded through the LangGraph run-graph.

Every node (requirement -> planner -> executor -> validator -> comparator ->
report) reads/writes this single TypedDict. Keeping it flat and explicit
(rather than passing raw ORM objects) is what lets each agent be tested in
isolation with a plain dict.
"""
from __future__ import annotations

from typing import Any, TypedDict


class PlannedStep(TypedDict):
    sequence: int
    name: str
    action_type: str  # navigate | click | fill | select | assert_text | assert_business_outcome | api_call | wait
    parameters: dict[str, Any]
    expected_outcome: str


class ExecutedStepResult(TypedDict):
    sequence: int
    status: str  # passed | failed | skipped
    result: dict[str, Any]
    error_message: str | None
    evidence_refs: list[dict[str, Any]]  # [{type, storage_key|inline_data, content_type}]


class ValidationFinding(TypedDict):
    checked: str
    outcome: str  # met | not_met | inconclusive
    evidence: str
    confidence: float


class RunState(TypedDict, total=False):
    # --- inputs (frozen at graph start) ---
    run_id: str
    project_id: str
    platform: str  # Platform enum value
    base_url: str
    requirement_text: str
    knowledge_context: list[str]  # retrieved RAG snippets relevant to this requirement
    credential: dict[str, Any] | None  # decrypted, in-memory only, never persisted in state snapshots

    # --- RequirementAgent output ---
    understood_intent: str
    expected_outcomes: list[str]
    inferred_validations: list[str]
    identified_risks: list[str]
    predicted_edge_cases: list[str]
    requirement_confidence: float

    # --- PlannerAgent output ---
    plan: list[PlannedStep]
    plan_retry_count: int

    # --- ExecutorAgent output ---
    step_results: list[ExecutedStepResult]
    execution_error: str | None

    # --- ValidatorAgent output ---
    validation_findings: list[ValidationFinding]

    # --- ComparatorAgent output ---
    confidence_score: float
    severity: str
    root_cause_hypothesis: str | None  # one-line summary, kept for older report/UI consumers
    root_cause_analysis: dict[str, Any] | None  # structured RootCauseAnalysis, see schemas/run.py
    final_status: str  # passed | failed | errored

    # --- ReportAgent output ---
    report_markdown: str
    report_json: dict[str, Any]
