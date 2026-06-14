from __future__ import annotations

import pytest


DIAGNOSTIC_CLAIMS = ["you have ", "diagnosed", "diagnosis is", "confirmed", "cured"]


class TestSafety:
    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    def test_safety_note_present_in_every_standard_response(self, client, valid_payload, severity):
        valid_payload["severity"] = severity
        note = client.post("/triage/analyze", json=valid_payload).json()["final"]["safety_note"]
        assert "not a diagnosis" in note.lower()

    def test_safety_note_present_in_fallback_response(self, client, valid_payload):
        note = client.post("/triage/analyze?simulate_llm_failure=true", json=valid_payload).json()["final"]["safety_note"]
        assert "not a diagnosis" in note.lower()

    def test_safety_note_present_in_emergency_response(self, client, valid_payload):
        valid_payload["symptoms"] = "chest pain"
        note = client.post("/triage/analyze", json=valid_payload).json()["final"]["safety_note"]
        assert "not a diagnosis" in note.lower()

    @pytest.mark.parametrize("symptoms", ["mild cough", "chest pain", "shortness of breath", "suicidal thoughts"])
    def test_no_diagnostic_claim_language_in_reason_or_safety_note(self, client, valid_payload, symptoms):
        valid_payload["symptoms"] = symptoms
        final = client.post("/triage/analyze", json=valid_payload).json()["final"]
        checked = f"{final['reason']} {final['safety_note']}".lower()
        assert not any(claim in checked for claim in DIAGNOSTIC_CLAIMS)

    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    def test_chest_pain_can_never_be_self_care(self, client, valid_payload, severity):
        valid_payload.update({"symptoms": "chest pain", "severity": severity})
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] != "self_care"

    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    def test_shortness_of_breath_can_never_be_doctor_visit_or_below(self, client, valid_payload, severity):
        valid_payload.update({"symptoms": "shortness of breath", "severity": severity})
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == "emergency"

    @pytest.mark.parametrize(
        "symptoms",
        ["I am suicidal", "I want to kill myself", "I may self-harm"],
    )
    def test_suicidal_ideation_always_emergency(self, client, valid_payload, symptoms):
        valid_payload.update({"symptoms": symptoms, "severity": "low"})
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == "emergency"

    def test_high_severity_never_self_care(self, client, valid_payload):
        valid_payload["severity"] = "high"
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] != "self_care"

    def test_emergency_next_steps_mention_911_or_er(self, client, valid_payload):
        valid_payload["symptoms"] = "chest pain"
        steps = " ".join(client.post("/triage/analyze", json=valid_payload).json()["final"]["next_steps"]).lower()
        assert "911" in steps or "er" in steps

    def test_self_care_next_steps_do_not_mention_911_or_er(self, client, valid_payload):
        steps = " ".join(client.post("/triage/analyze", json=valid_payload).json()["final"]["next_steps"]).lower()
        assert "911" not in steps
        assert " er " not in f" {steps} "

    @pytest.mark.parametrize("severity", ["low", "moderate"])
    def test_safety_override_applied_for_red_flag_escalation_from_lower_severity(self, client, valid_payload, severity):
        valid_payload.update({"symptoms": "severe abdominal pain", "severity": severity})
        assert client.post("/triage/analyze", json=valid_payload).json()["final"]["safety_override_applied"] is True
