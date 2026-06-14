from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import CASE_STORE, app  # noqa: E402
from app.schemas import TriageRequest  # noqa: E402


@pytest.fixture(autouse=True)
def clear_case_store():
    CASE_STORE.clear()
    yield
    CASE_STORE.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "change-me"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "age": 25,
        "symptoms": "mild runny nose",
        "duration": "since morning",
        "severity": "low",
        "medical_history": None,
        "current_medications": None,
        "allergies": None,
        "pregnant_or_immunocompromised": False,
    }


@pytest.fixture
def valid_request(valid_payload: dict[str, object]) -> TriageRequest:
    return TriageRequest.model_validate(valid_payload)


DEMO_SCENARIOS = [
    (
        "self_care",
        {
            "age": 25,
            "symptoms": "mild runny nose and sneezing",
            "duration": "since this morning",
            "severity": "low",
            "medical_history": None,
            "current_medications": None,
            "allergies": None,
            "pregnant_or_immunocompromised": False,
        },
    ),
    (
        "doctor_visit",
        {
            "age": 42,
            "symptoms": "cough that is not going away",
            "duration": "10 days",
            "severity": "moderate",
            "medical_history": None,
            "current_medications": None,
            "allergies": None,
            "pregnant_or_immunocompromised": False,
        },
    ),
    (
        "urgent_care",
        {
            "age": 31,
            "symptoms": "painful swollen ankle after twisting it and can barely walk",
            "duration": "2 hours",
            "severity": "high",
            "medical_history": None,
            "current_medications": None,
            "allergies": None,
            "pregnant_or_immunocompromised": False,
        },
    ),
    (
        "emergency",
        {
            "age": 54,
            "symptoms": "chest tightness, sweating, and shortness of breath",
            "duration": "30 minutes",
            "severity": "high",
            "medical_history": None,
            "current_medications": None,
            "allergies": None,
            "pregnant_or_immunocompromised": False,
        },
    ),
]


RED_FLAG_CASES = [
    ("chest pain", "I have chest pain now"),
    ("chest tightness", "I feel chest tightness"),
    ("chest pressure", "There is chest pressure"),
    ("shortness of breath", "I have shortness of breath"),
    ("trouble breathing", "I am having trouble breathing"),
    ("cannot breathe", "I can't breathe normally"),
    ("profuse sweating", "I have profuse sweating"),
    ("cold sweating", "I woke with cold sweating"),
    ("sudden severe headache", "A sudden severe headache started"),
    ("face drooping", "My face drooping started suddenly"),
    ("slurred speech", "I have slurred speech"),
    ("sudden confusion", "There is sudden confusion"),
    ("stroke symptoms", "These feel like stroke symptoms"),
    ("loss of consciousness", "There was loss of consciousness"),
    ("loss of consciousness", "I was unconscious"),
    ("fainting", "I keep fainting"),
    ("suicidal ideation", "I am suicidal"),
    ("suicidal ideation", "I want to kill myself"),
    ("self-harm", "I may self-harm tonight"),
    ("anaphylaxis", "This feels like anaphylaxis"),
    ("severe allergic reaction", "I have a severe allergic reaction"),
    ("throat swelling", "My throat swelling is getting worse"),
    ("throat swelling", "My lips swelling started"),
    ("vomiting blood", "I am vomiting blood"),
    ("blood in stool", "There is blood in stool"),
    ("black stool", "I noticed black stool"),
    ("uncontrolled bleeding", "I have uncontrolled bleeding"),
    ("uncontrolled bleeding", "The wound won't stop bleeding"),
    ("cardiac emergency", "I think this is a heart attack"),
    ("seizure", "I had a seizure"),
    ("severe abdominal pain", "I have severe abdominal pain"),
]


BENIGN_CASES = [
    "I have chest muscle soreness after exercise but no chest pain",
    "I am out of breath after sprinting but recovered quickly",
    "I watched a movie about a heart attack but feel fine",
    "I am worried about stroke prevention but no symptoms",
    "My stool is dark after iron tablets, no black stool description",
    "I donated blood and feel okay",
    "I read about seizures for school",
    "My allergy pills mention anaphylaxis in the leaflet",
]
