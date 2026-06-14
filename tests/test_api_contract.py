from __future__ import annotations

import uuid

import pytest


class TestApiContract:
    def test_response_contains_every_required_top_level_field(self, client, valid_payload):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert {"case_id", "triage_level", "final", "symptom_analyzer", "care_guidance", "supervisor", "graph"} <= set(body)

    @pytest.mark.parametrize(
        "field",
        ["final_triage_level", "reason", "next_steps", "safety_note", "safety_override_applied"],
    )
    def test_final_contains_every_required_field(self, client, valid_payload, field):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert field in body["final"]

    @pytest.mark.parametrize(
        "field",
        ["symptoms_extracted", "severity_assessment", "duration_assessment", "category", "red_flags", "red_flag_detected"],
    )
    def test_symptom_analyzer_contains_every_required_field(self, client, valid_payload, field):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert field in body["symptom_analyzer"]

    @pytest.mark.parametrize("field", ["recommended_level", "reasoning", "next_steps"])
    def test_care_guidance_contains_every_required_field(self, client, valid_payload, field):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert field in body["care_guidance"]

    @pytest.mark.parametrize("field", ["nodes_visited", "path"])
    def test_graph_contains_every_required_field(self, client, valid_payload, field):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert field in body["graph"]

    def test_case_id_is_uuid_string(self, client, valid_payload):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert str(uuid.UUID(body["case_id"])) == body["case_id"]

    def test_triage_level_matches_final_triage_level(self, client, valid_payload):
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert body["triage_level"] == body["final"]["final_triage_level"]

    def test_unique_case_ids(self, client, valid_payload):
        ids = [client.post("/triage/analyze", json=valid_payload).json()["case_id"] for _ in range(10)]
        assert len(ids) == len(set(ids))

    def test_json_content_type_header(self, client, valid_payload):
        response = client.post("/triage/analyze", json=valid_payload)
        assert response.headers["content-type"].startswith("application/json")

    def test_get_cases_list_shape(self, client, valid_payload, auth_headers):
        client.post("/triage/analyze", json=valid_payload)
        body = client.get("/cases", headers=auth_headers).json()
        assert len(body) == 1
        assert {"case_id", "age", "symptoms", "duration", "severity", "triage_level"} <= set(body[0])

    def test_get_case_by_id_200(self, client, valid_payload, auth_headers):
        created = client.post("/triage/analyze", json=valid_payload).json()
        response = client.get(f"/cases/{created['case_id']}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["case_id"] == created["case_id"]

    def test_get_case_by_id_404(self, client, auth_headers):
        response = client.get(f"/cases/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404

    def test_get_cases_requires_auth(self, client):
        assert client.get("/cases").status_code == 401

    def test_get_case_requires_auth(self, client):
        assert client.get(f"/cases/{uuid.uuid4()}").status_code == 401

    def test_auth_login_success(self, client):
        response = client.post("/auth/login", json={"username": "admin", "password": "change-me"})
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

    @pytest.mark.parametrize(
        "payload",
        [
            {"username": "admin", "password": "wrong"},
            {"username": "wrong", "password": "change-me"},
            {"username": "wrong", "password": "wrong"},
        ],
    )
    def test_auth_login_failure(self, client, payload):
        assert client.post("/auth/login", json=payload).status_code == 401

    @pytest.mark.parametrize("payload", [{"username": "admin"}, {"password": "change-me"}, {}])
    def test_auth_login_missing_fields(self, client, payload):
        assert client.post("/auth/login", json=payload).status_code == 422

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("get", "/triage/analyze"),
            ("put", "/triage/analyze"),
            ("delete", "/triage/analyze"),
            ("post", "/health"),
            ("put", "/cases"),
            ("post", "/cases/not-real"),
        ],
    )
    def test_http_method_enforcement_405s(self, client, method, path):
        assert getattr(client, method)(path).status_code == 405

    def test_unknown_route_404(self, client):
        assert client.get("/unknown-route").status_code == 404


class TestApiContractMatrix:
    @pytest.mark.parametrize("severity", ["low", "moderate", "high"])
    @pytest.mark.parametrize("age", [0, 1, 18, 65, 105, 120])
    def test_contract_stable_across_age_and_severity_matrix(self, client, valid_payload, severity, age):
        valid_payload.update({"severity": severity, "age": age})
        body = client.post("/triage/analyze", json=valid_payload).json()
        assert body["final"]["next_steps"]
        assert isinstance(body["graph"]["nodes_visited"], list)
