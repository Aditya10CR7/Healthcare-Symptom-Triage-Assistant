from __future__ import annotations

import pytest

from conftest import DEMO_SCENARIOS


class TestFrontendBehavior:
    @pytest.mark.parametrize(
        "missing_field",
        ["age", "symptoms", "duration", "severity"],
    )
    def test_required_fields_rejected_when_missing_matching_disabled_form_state(self, client, valid_payload, missing_field):
        valid_payload.pop(missing_field)
        assert client.post("/triage/analyze", json=valid_payload).status_code == 422

    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    def test_all_three_severity_selector_values_are_accepted(self, client, valid_payload, severity):
        valid_payload["severity"] = severity
        assert client.post("/triage/analyze", json=valid_payload).status_code == 200

    @pytest.mark.parametrize(("expected", "payload"), DEMO_SCENARIOS)
    def test_demo_scenario_cards_return_200_and_expected_level(self, client, expected, payload):
        response = client.post("/triage/analyze", json=payload)
        assert response.status_code == 200
        assert response.json()["triage_level"] == expected

    def test_result_panel_shape_has_non_empty_display_fields(self, client, valid_payload):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert body["triage_level"]
        assert body["final"]["reason"]
        assert body["final"]["next_steps"]
        assert body["final"]["safety_note"]

    def test_developer_trace_contains_graph_path_and_nodes(self, client, valid_payload):
        graph = client.post("/triage/analyze", json=valid_payload).json()["graph"]
        assert isinstance(graph["nodes_visited"], list)
        assert graph["path"] == "→".join(graph["nodes_visited"])

    @pytest.mark.parametrize("trace_key", ["symptom_analyzer", "care_guidance", "supervisor"])
    def test_developer_trace_raw_json_sections_are_accessible(self, client, valid_payload, trace_key):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert isinstance(body[trace_key], dict)
        assert body[trace_key]

    @pytest.mark.parametrize(
        ("severity", "expected"),
        [("low", "self_care"), ("moderate", "doctor_visit"), ("high", "urgent_care")],
    )
    def test_result_panel_level_changes_with_severity_selector(self, client, valid_payload, severity, expected):
        valid_payload["severity"] = severity
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == expected
