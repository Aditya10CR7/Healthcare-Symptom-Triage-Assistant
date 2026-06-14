import pytest

from app.config import get_settings
from app.schemas import TriageIntake
import app.triage_graph as triage_graph_module
from app.triage_graph import run_triage


@pytest.fixture(autouse=True)
def force_deterministic_tests(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_emergency_red_flags_override_to_emergency():
    response = run_triage(
        TriageIntake(
            age=54,
            symptoms="chest tightness, sweating, and shortness of breath",
            duration="30 minutes",
            severity="high",
        )
    )

    assert response.triage_level == "emergency"
    assert response.symptom_analyzer is not None
    assert response.symptom_analyzer.red_flags is True
    assert "supervisor_node" in response.graph.visited_nodes


def test_mild_symptoms_can_use_self_care():
    response = run_triage(
        TriageIntake(
            age=25,
            symptoms="mild runny nose and sneezing",
            duration="since this morning",
            severity="low",
        )
    )

    assert response.triage_level == "self_care"
    assert response.care_guidance is not None
    assert response.graph.used_llm is False
    assert response.graph.provider == "deterministic"


def test_high_severity_minimum_is_urgent_care():
    response = run_triage(
        TriageIntake(
            age=31,
            symptoms="painful swollen ankle after twisting it and can barely walk",
            duration="2 hours",
            severity="high",
        )
    )

    assert response.triage_level in {"urgent_care", "emergency"}


def test_no_database_session_still_returns_normal_response():
    response = run_triage(
        TriageIntake(
            age=25,
            symptoms="mild runny nose and sneezing",
            duration="since this morning",
            severity="low",
        ),
        db=None,
    )

    assert response.triage_level == "self_care"
    assert response.graph.fallback_reason is None
    assert "persist_case_node" in response.graph.visited_nodes


def test_llm_node_failure_preserves_emergency_escalation(monkeypatch):
    def raise_for_care_guidance(schema, prompt):
        if schema.__name__ == "CareGuidanceOutput":
            raise RuntimeError("structured output failed")
        return None

    monkeypatch.setattr(triage_graph_module, "_invoke_structured", raise_for_care_guidance)

    response = run_triage(
        TriageIntake(
            age=54,
            symptoms="chest tightness, sweating, and shortness of breath",
            duration="30 minutes",
            severity="high",
        ),
        db=None,
    )

    assert response.triage_level == "emergency"
    assert response.care_guidance is not None
    assert response.graph.fallback_reason == "Care guidance LLM output failed; deterministic guidance used."
    assert response.final.safety_note.lower().count("not a diagnosis") == 1
