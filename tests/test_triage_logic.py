from __future__ import annotations

import pytest

from app.triage_graph import detect_category, run_triage_graph
from app.schemas import TriageRequest


class TestTriageLogic:
    @pytest.mark.parametrize(
        ("severity", "symptoms", "expected"),
        [
            ("low", "mild runny nose", "self_care"),
            ("moderate", "persistent cough", "doctor_visit"),
            ("high", "painful swollen ankle", "urgent_care"),
            ("low", "chest pain", "emergency"),
        ],
    )
    def test_happy_path_for_all_four_levels(self, client, valid_payload, severity, symptoms, expected):
        valid_payload.update({"severity": severity, "symptoms": symptoms})
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == expected

    @pytest.mark.parametrize(
        "symptoms",
        ["ankle pain", "bad headache", "high fever", "back pain", "vomiting", "rash"],
    )
    def test_high_severity_floor_is_urgent_care_or_higher(self, client, valid_payload, symptoms):
        valid_payload.update({"severity": "high", "symptoms": symptoms})
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] in {"urgent_care", "emergency"}

    @pytest.mark.parametrize("low_severity", ["low"])
    @pytest.mark.parametrize("moderate_severity", ["moderate"])
    @pytest.mark.parametrize("high_severity", ["high"])
    def test_monotonic_escalation_ordering_without_red_flags(self, valid_payload, low_severity, moderate_severity, high_severity):
        order = {"self_care": 0, "doctor_visit": 1, "urgent_care": 2, "emergency": 3}
        base = dict(valid_payload)
        base["symptoms"] = "non specific fatigue"
        low = run_triage_graph(TriageRequest.model_validate({**base, "severity": low_severity})).triage_level
        moderate = run_triage_graph(TriageRequest.model_validate({**base, "severity": moderate_severity})).triage_level
        high = run_triage_graph(TriageRequest.model_validate({**base, "severity": high_severity})).triage_level
        assert order[low] <= order[moderate] <= order[high]

    @pytest.mark.parametrize("age", [0, 105, 120])
    def test_age_edge_cases_are_accepted(self, client, valid_payload, age):
        valid_payload["age"] = age
        assert client.post("/triage/analyze", json=valid_payload).status_code == 200

    @pytest.mark.parametrize(
        ("severity", "expected"),
        [("low", "doctor_visit"), ("moderate", "doctor_visit"), ("high", "urgent_care")],
    )
    def test_pregnant_or_immunocompromised_context_is_conservative(self, client, valid_payload, severity, expected):
        valid_payload.update({"severity": severity, "pregnant_or_immunocompromised": True})
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == expected

    @pytest.mark.parametrize(
        ("text", "category"),
        [
            ("chest pressure", "cardiac"),
            ("wheezing cough", "respiratory"),
            ("slurred speech", "neurological"),
            ("twisted ankle injury", "injury"),
            ("fever and chills", "infection"),
            ("severe abdominal pain", "abdominal"),
            ("allergic reaction", "allergic"),
            ("suicidal thoughts", "mental_health"),
            ("mild tiredness", "general"),
        ],
    )
    def test_symptom_category_detection(self, text, category):
        assert detect_category(text) == category
