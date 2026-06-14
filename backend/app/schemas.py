from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Severity = Literal["low", "moderate", "high"]
TriageLevel = Literal["self_care", "doctor_visit", "urgent_care", "emergency"]


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: int = Field(..., ge=0, le=120)
    symptoms: str = Field(..., min_length=3, max_length=4000)
    duration: str = Field(..., min_length=1, max_length=200)
    severity: Severity
    medical_history: str | None = Field(default=None, max_length=2000)
    current_medications: str | None = Field(default=None, max_length=1000)
    allergies: str | None = Field(default=None, max_length=500)
    pregnant_or_immunocompromised: bool = False

    @field_validator("age", mode="before")
    @classmethod
    def reject_bool_and_non_int_age(cls, value: object) -> object:
        if isinstance(value, bool) or isinstance(value, float):
            raise ValueError("age must be an integer")
        return value

    @field_validator("symptoms", "duration")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value


class SymptomAnalyzerOutput(BaseModel):
    symptoms_extracted: list[str]
    severity_assessment: Severity
    duration_assessment: str
    category: str
    red_flags: list[str]
    red_flag_detected: bool


class CareGuidanceOutput(BaseModel):
    recommended_level: TriageLevel
    reasoning: str
    next_steps: list[str]


class SupervisorOutput(BaseModel):
    final_triage_level: TriageLevel
    reason: str
    next_steps: list[str]
    safety_note: str
    safety_override_applied: bool


class GraphOutput(BaseModel):
    nodes_visited: list[str]
    path: str


class TriageResponse(BaseModel):
    case_id: str
    triage_level: TriageLevel
    final: SupervisorOutput
    symptom_analyzer: SymptomAnalyzerOutput
    care_guidance: CareGuidanceOutput
    supervisor: SupervisorOutput
    graph: GraphOutput


class CaseSummary(BaseModel):
    case_id: str
    age: int
    symptoms: str
    duration: str
    severity: Severity
    triage_level: TriageLevel


class CaseDetail(CaseSummary):
    final: SupervisorOutput
    symptom_analyzer: SymptomAnalyzerOutput
    care_guidance: CareGuidanceOutput
    supervisor: SupervisorOutput
    graph: GraphOutput


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Compatibility alias for older local imports.
TriageIntake = TriageRequest
