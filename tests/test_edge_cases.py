from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import TriageRequest
from app.triage_graph import run_triage_graph
from conftest import DEMO_SCENARIOS


class TestEdgeCases:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("age", 0),
            ("age", 120),
            ("symptoms", "abc"),
            ("symptoms", "a" * 4000),
            ("duration", "x"),
            ("duration", "x" * 200),
            ("medical_history", "x" * 2000),
            ("current_medications", "x" * 1000),
            ("allergies", "x" * 500),
        ],
    )
    def test_exact_boundary_values(self, client, valid_payload, field, value):
        valid_payload[field] = value
        assert client.post("/triage/analyze", json=valid_payload).status_code == 200

    @pytest.mark.parametrize(
        "symptoms",
        ["CHEST PAIN", "SHORTNESS OF BREATH", "SLURRED SPEECH", "SEVERE ABDOMINAL PAIN"],
    )
    def test_all_caps_red_flag_text(self, client, valid_payload, symptoms):
        valid_payload["symptoms"] = symptoms
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == "emergency"

    @pytest.mark.parametrize(
        "symptoms",
        ["J'ai mal a la tete depuis ce matin", "Tengo tos leve", "لدي صداع خفيف", "У меня легкий кашель"],
    )
    def test_unicode_symptoms_are_accepted(self, client, valid_payload, symptoms):
        valid_payload["symptoms"] = symptoms
        assert client.post("/triage/analyze", json=valid_payload).status_code == 200

    def test_red_flag_buried_in_long_text(self, client, valid_payload):
        valid_payload["symptoms"] = f"{'mild discomfort ' * 100} then sudden severe headache"
        assert client.post("/triage/analyze", json=valid_payload).json()["triage_level"] == "emergency"

    def test_red_flag_in_medication_field_must_not_affect_triage(self, client, valid_payload):
        valid_payload["current_medications"] = "Medication pamphlet says seek care for chest pain"
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert body["triage_level"] == "self_care"
        assert body["symptom_analyzer"]["red_flags"] == []

    def test_ten_concurrent_threaded_requests(self, valid_payload):
        def send(index: int) -> str:
            with TestClient(app) as local_client:
                payload = {**valid_payload, "symptoms": f"mild cough {index}"}
                return local_client.post("/triage/analyze", json=payload).json()["case_id"]

        with ThreadPoolExecutor(max_workers=10) as pool:
            ids = list(pool.map(send, range(10)))
        assert len(ids) == len(set(ids)) == 10

    def test_same_payload_determinism_over_five_runs(self, valid_request):
        levels = [run_triage_graph(valid_request).triage_level for _ in range(5)]
        assert levels == ["self_care"] * 5

    @pytest.mark.parametrize(("expected", "payload"), DEMO_SCENARIOS)
    def test_all_demo_scenario_cards(self, client, expected, payload):
        response = client.post("/triage/analyze", json=payload)
        assert response.status_code == 200
        assert response.json()["triage_level"] == expected

    def test_simulate_llm_failure_end_to_end(self, client, valid_payload):
        response = client.post("/triage/analyze?simulate_llm_failure=true", json=valid_payload)
        assert response.status_code == 200
        assert response.json()["graph"]["nodes_visited"] == ["validate_intake", "fallback", "persist_case"]

    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    @pytest.mark.parametrize("symptoms", ["mild cough", "ankle pain", "rash", "stomach upset", "fatigue"])
    def test_deterministic_direct_runner_matrix(self, valid_payload, severity, symptoms):
        request = TriageRequest.model_validate({**valid_payload, "severity": severity, "symptoms": symptoms})
        first = run_triage_graph(request).triage_level
        second = run_triage_graph(request).triage_level
        assert first == second
