from __future__ import annotations

import pytest

from app.triage_graph import detect_red_flags
from conftest import BENIGN_CASES, RED_FLAG_CASES


class TestRedFlags:
    @pytest.mark.parametrize(("expected", "text"), RED_FLAG_CASES)
    def test_detect_red_flags_positive_patterns(self, expected, text):
        flags = detect_red_flags(text)
        assert expected in flags

    @pytest.mark.parametrize("text", BENIGN_CASES)
    def test_detect_red_flags_benign_false_positive_checks(self, text):
        assert detect_red_flags(text) == []

    @pytest.mark.parametrize(("expected", "symptoms"), RED_FLAG_CASES)
    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    def test_api_each_red_flag_type_is_emergency_across_all_severities(self, client, valid_payload, expected, symptoms, severity):
        valid_payload.update({"symptoms": symptoms, "severity": severity})
        response = client.post("/triage/analyze", json=valid_payload)
        body = response.json()
        assert response.status_code == 200
        assert body["triage_level"] == "emergency"
        assert expected in body["symptom_analyzer"]["red_flags"]

    @pytest.mark.parametrize("severity", ["low", "moderate"])
    def test_supervisor_override_true_when_low_or_moderate_red_flag_forces_emergency(self, client, valid_payload, severity):
        valid_payload.update({"symptoms": "chest pain", "severity": severity})
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert body["final"]["final_triage_level"] == "emergency"
        assert body["final"]["safety_override_applied"] is True

    def test_supervisor_override_false_when_high_red_flag_already_emergency(self, client, valid_payload):
        valid_payload.update({"symptoms": "chest pain", "severity": "high"})
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert body["triage_level"] == "emergency"
        assert body["final"]["safety_override_applied"] is False

    def test_multiple_simultaneous_red_flags_are_all_reported(self, client, valid_payload):
        valid_payload["symptoms"] = "chest pain with shortness of breath, slurred speech, and vomiting blood"
        body = client.post("/triage/analyze", json=valid_payload).json()
        flags = body["symptom_analyzer"]["red_flags"]
        assert body["triage_level"] == "emergency"
        assert {"chest pain", "shortness of breath", "slurred speech", "vomiting blood"}.issubset(flags)
