"""Deterministic transform of a run's report_json into Jira wiki markup, so
a failed run can be pasted straight into a bug ticket.
"""
from __future__ import annotations

from typing import Any


def render_jira(report_json: dict[str, Any]) -> str:
    lines = [
        f"h2. {report_json.get('requirement_text', 'Requirement')}",
        "",
        f"*Status:* {report_json.get('final_status', 'unknown')}",
        f"*Confidence:* {report_json.get('confidence_score', 'n/a')}",
        f"*Severity:* {report_json.get('severity', 'n/a')}",
        "",
        "h3. Root Cause",
        report_json.get("root_cause_hypothesis") or "_Not applicable — run passed._",
        "",
        "h3. Validation Findings",
    ]
    for finding in report_json.get("validation_findings", []) or []:
        icon = {"met": "(/)", "not_met": "(x)", "inconclusive": "(?)"}.get(finding.get("outcome"), "(?)")
        lines.append(f"{icon} *{finding.get('checked')}* — {finding.get('evidence')}")

    lines += ["", "h3. Steps"]
    for step in report_json.get("plan", []) or []:
        lines.append(f"# {step.get('name')} ({step.get('action_type')})")

    return "\n".join(lines)
