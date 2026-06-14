from __future__ import annotations

import pytest


class TestValidation:
    @pytest.mark.parametrize(
        ("age", "status"),
        [(0, 200), (120, 200), (-1, 422), (121, 422), (None, 422), ("25", 200), (25.5, 422)],
    )
    def test_age_bounds_and_types(self, client, valid_payload, age, status):
        valid_payload["age"] = age
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == status

    @pytest.mark.parametrize(
        ("symptoms", "status"),
        [("abc", 200), ("a" * 4000, 200), ("a" * 4001, 422), ("", 422), ("   ", 422), ("頭痛と吐き気", 200), ("rash + fever!!!", 200)],
    )
    def test_symptoms_length_blank_unicode_and_special_chars(self, client, valid_payload, symptoms, status):
        valid_payload["symptoms"] = symptoms
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == status

    @pytest.mark.parametrize(
        ("duration", "status"),
        [("x", 200), ("a" * 200, 200), ("a" * 201, 422), ("", 422), ("   ", 422), (None, 422)],
    )
    def test_duration_bounds_and_blank_values(self, client, valid_payload, duration, status):
        valid_payload["duration"] = duration
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == status

    @pytest.mark.parametrize(
        ("severity", "status"),
        [("low", 200), ("moderate", 200), ("high", 200), ("LOW", 422), ("medium", 422), ("", 422), (None, 422)],
    )
    def test_severity_enum_values(self, client, valid_payload, severity, status):
        valid_payload["severity"] = severity
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == status

    @pytest.mark.parametrize(
        ("field", "max_len"),
        [("medical_history", 2000), ("current_medications", 1000), ("allergies", 500)],
    )
    def test_optional_fields_accept_exact_max_length(self, client, valid_payload, field, max_len):
        valid_payload[field] = "x" * max_len
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ("field", "max_len"),
        [("medical_history", 2000), ("current_medications", 1000), ("allergies", 500)],
    )
    def test_optional_fields_reject_one_over_max_length(self, client, valid_payload, field, max_len):
        valid_payload[field] = "x" * (max_len + 1)
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "patch",
        [
            {"age": -1, "symptoms": "", "duration": "", "severity": "bad"},
            {"age": 121, "symptoms": "  ", "duration": "  "},
            {"age": None, "symptoms": None, "duration": None, "severity": None},
            {"symptoms": "ab", "medical_history": "x" * 2001},
            {"duration": "x" * 201, "allergies": "x" * 501},
            {"current_medications": "x" * 1001, "severity": "urgent"},
            {"age": 3.14, "pregnant_or_immunocompromised": "not-bool"},
            {"symptoms": [], "duration": {}, "severity": []},
            {"unknown": "field"},
            {"age": True},
        ],
    )
    def test_compound_malformed_payloads_fail_validation(self, client, valid_payload, patch):
        valid_payload.update(patch)
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.status_code == 422
