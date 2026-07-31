from app.agents.comparator_agent import _compute_confidence


def _state(**overrides):
    base = {
        "execution_error": None,
        "validation_findings": [],
        "step_results": [],
    }
    base.update(overrides)
    return base


def test_execution_error_yields_zero_confidence_and_errored():
    score, status = _compute_confidence(_state(execution_error="login failed"))
    assert score == 0.0
    assert status == "errored"


def test_no_findings_yields_errored():
    score, status = _compute_confidence(_state())
    assert score == 0.0
    assert status == "errored"


def test_all_findings_met_with_passing_steps_yields_high_confidence_pass():
    state = _state(
        validation_findings=[
            {"checked": "invoice appears", "outcome": "met", "evidence": "grid shows row", "confidence": 0.9},
            {"checked": "audit log written", "outcome": "met", "evidence": "log entry present", "confidence": 0.85},
        ],
        step_results=[{"sequence": 1, "status": "passed"}, {"sequence": 2, "status": "passed"}],
    )
    score, status = _compute_confidence(state)
    assert status == "passed"
    assert score > 0.6


def test_any_not_met_finding_forces_failed_even_with_high_score():
    state = _state(
        validation_findings=[
            {"checked": "invoice appears", "outcome": "met", "evidence": "grid shows row", "confidence": 0.95},
            {"checked": "balance updates", "outcome": "not_met", "evidence": "balance unchanged", "confidence": 0.9},
        ],
        step_results=[{"sequence": 1, "status": "passed"}],
    )
    score, status = _compute_confidence(state)
    assert status == "failed"


def test_failed_step_forces_failed_status():
    state = _state(
        validation_findings=[
            {"checked": "invoice appears", "outcome": "met", "evidence": "grid shows row", "confidence": 0.9},
        ],
        step_results=[{"sequence": 1, "status": "failed"}],
    )
    _, status = _compute_confidence(state)
    assert status == "failed"
