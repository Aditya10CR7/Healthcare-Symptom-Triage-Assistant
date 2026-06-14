from __future__ import annotations

import pytest

from app.schemas import TriageRequest
from app.triage_graph import (
    care_guidance_node,
    fallback_node,
    persist_case_node,
    run_triage_graph,
    supervisor_node,
    symptom_analyzer_node,
    validate_intake_node,
)


class TestGraphWorkflow:
    def test_happy_path_node_execution_order(self, valid_request):
        response = run_triage_graph(valid_request)
        assert response.graph.nodes_visited == [
            "validate_intake",
            "symptom_analyzer",
            "care_guidance",
            "supervisor",
            "persist_case",
        ]

    def test_fallback_path_skips_analyzer_guidance_and_supervisor_nodes(self, valid_request):
        response = run_triage_graph(valid_request, simulate_llm_failure=True)
        assert response.graph.nodes_visited == ["validate_intake", "fallback", "persist_case"]
        assert response.graph.path == "validate_intake→fallback→persist_case"

    def test_fallback_preserves_emergency_for_red_flags(self, valid_payload):
        request = TriageRequest.model_validate({**valid_payload, "symptoms": "chest pain", "severity": "low"})
        response = run_triage_graph(request, simulate_llm_failure=True)
        assert response.triage_level == "emergency"
        assert response.final.safety_override_applied is True

    def test_no_database_session_operation(self, valid_request):
        response = run_triage_graph(valid_request, db_session=None)
        assert response.case_id
        assert "persist_case" in response.graph.nodes_visited

    def test_validate_intake_node_mutates_state(self, valid_payload):
        state = {"request": valid_payload, "nodes_visited": []}
        validate_intake_node(state)
        assert state["nodes_visited"] == ["validate_intake"]
        assert isinstance(state["request"], TriageRequest)

    def test_symptom_analyzer_node_outputs_expected_shape(self, valid_request):
        state = {"request": valid_request, "nodes_visited": []}
        symptom_analyzer_node(state)
        assert state["symptom_analyzer"].symptoms_extracted
        assert state["symptom_analyzer"].red_flag_detected is False

    def test_care_guidance_node_outputs_expected_shape(self, valid_request):
        state = {"request": valid_request, "nodes_visited": []}
        symptom_analyzer_node(state)
        care_guidance_node(state)
        assert state["care_guidance"].recommended_level == "self_care"
        assert state["care_guidance"].next_steps

    def test_supervisor_node_outputs_expected_shape(self, valid_request):
        state = {"request": valid_request, "nodes_visited": []}
        symptom_analyzer_node(state)
        care_guidance_node(state)
        supervisor_node(state)
        assert state["final"].final_triage_level == "self_care"
        assert state["supervisor"].safety_note

    def test_fallback_node_outputs_full_response_components(self, valid_request):
        state = {"request": valid_request, "nodes_visited": []}
        fallback_node(state)
        assert state["symptom_analyzer"]
        assert state["care_guidance"]
        assert state["final"]

    def test_persist_case_node_adds_case_id(self, valid_request):
        state = {"request": valid_request, "nodes_visited": []}
        persist_case_node(state)
        assert state["case_id"]
        assert state["nodes_visited"] == ["persist_case"]

    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    def test_each_node_path_handles_all_severities(self, valid_payload, severity):
        request = TriageRequest.model_validate({**valid_payload, "severity": severity})
        response = run_triage_graph(request)
        assert response.final.final_triage_level == response.triage_level
