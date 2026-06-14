from __future__ import annotations

import re
import uuid
from typing import Any

from app.schemas import (
    CareGuidanceOutput,
    GraphOutput,
    Severity,
    SupervisorOutput,
    SymptomAnalyzerOutput,
    TriageLevel,
    TriageRequest,
    TriageResponse,
)


LEVEL_ORDER: list[TriageLevel] = ["self_care", "doctor_visit", "urgent_care", "emergency"]

RED_FLAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("chest pain", re.compile(r"\bchest\s+pain\b", re.I)),
    ("chest tightness", re.compile(r"\bchest\s+tight(ness)?\b", re.I)),
    ("chest pressure", re.compile(r"\bchest\s+pressure\b", re.I)),
    ("shortness of breath", re.compile(r"\bshort(ness)?\s+of\s+breath\b", re.I)),
    ("trouble breathing", re.compile(r"\b(trouble|difficulty|hard time)\s+breathing\b", re.I)),
    ("cannot breathe", re.compile(r"\b(can'?t|cannot)\s+breathe\b", re.I)),
    ("profuse sweating", re.compile(r"\b(profuse|heavy|cold)\s+sweat(ing)?\b", re.I)),
    ("cold sweating", re.compile(r"\bcold\s+sweat(ing)?\b", re.I)),
    ("sudden severe headache", re.compile(r"\bsudden\s+(severe|worst)\s+headache\b", re.I)),
    ("face drooping", re.compile(r"\b(face\s+droop(ing)?|drooping\s+face)\b", re.I)),
    ("slurred speech", re.compile(r"\bslurred\s+speech\b", re.I)),
    ("sudden confusion", re.compile(r"\bsudden\s+confusion\b", re.I)),
    ("stroke symptoms", re.compile(r"\bstroke(-like)?\s+symptoms?\b", re.I)),
    ("loss of consciousness", re.compile(r"\b(loss\s+of\s+consciousness|unconscious|passed\s+out)\b", re.I)),
    ("fainting", re.compile(r"\b(fainting|fainted)\b", re.I)),
    ("suicidal ideation", re.compile(r"\b(suicidal|suicide|kill\s+myself)\b", re.I)),
    ("self-harm", re.compile(r"\bself[-\s]?harm\b", re.I)),
    ("anaphylaxis", re.compile(r"\banaphylaxis\b", re.I)),
    ("severe allergic reaction", re.compile(r"\bsevere\s+allergic\s+reaction\b", re.I)),
    ("throat swelling", re.compile(r"\b(throat|tongue|lips?)\s+swelling\b", re.I)),
    ("vomiting blood", re.compile(r"\b(vomiting|throwing\s+up)\s+blood\b", re.I)),
    ("blood in stool", re.compile(r"\bblood\s+in\s+(stool|poop)\b", re.I)),
    ("black stool", re.compile(r"\bblack\s+(stool|tarry\s+stool)\b", re.I)),
    ("uncontrolled bleeding", re.compile(r"\b(uncontrolled|severe|won'?t\s+stop)\s+bleeding\b", re.I)),
    ("cardiac emergency", re.compile(r"\b(cardiac\s+emergency|heart\s+attack)\b", re.I)),
    ("seizure", re.compile(r"\bseizure\b", re.I)),
    ("severe abdominal pain", re.compile(r"\bsevere\s+(abdominal|stomach|belly)\s+pain\b", re.I)),
]


def _state_append(state: dict[str, Any], node_name: str) -> dict[str, Any]:
    state.setdefault("nodes_visited", []).append(node_name)
    return state


def _analysis_text(request: TriageRequest) -> str:
    # Current medications are intentionally excluded so a red-flag drug name or
    # instruction in that field cannot escalate triage by itself.
    return " ".join(
        part
        for part in [
            request.symptoms,
            request.duration,
            request.medical_history or "",
            request.allergies or "",
        ]
        if part
    )


def _is_contextual_false_positive(text: str, match: re.Match[str]) -> bool:
    before = text[max(0, match.start() - 32) : match.start()].lower()
    around = text[max(0, match.start() - 48) : min(len(text), match.end() + 48)].lower()
    if re.search(r"\b(no|without|denies|denied)\s+$", before):
        return True
    return any(
        phrase in around
        for phrase in [
            "movie about",
            "read about",
            "worried about",
            "prevention",
            "mention",
            "leaflet",
            "pamphlet",
            "description",
            "feel fine",
        ]
    )


def detect_red_flags(text: str) -> list[str]:
    matches = []
    for name, pattern in RED_FLAG_PATTERNS:
        match = pattern.search(text)
        if match and not _is_contextual_false_positive(text, match):
            matches.append(name)
    return sorted(set(matches))


def detect_category(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["chest", "heart", "cardiac"]):
        return "cardiac"
    if any(word in lower for word in ["breath", "cough", "wheez", "asthma"]):
        return "respiratory"
    if any(word in lower for word in ["face droop", "slurred", "confusion", "seizure", "headache", "stroke"]):
        return "neurological"
    if any(word in lower for word in ["ankle", "twist", "fall", "fracture", "sprain", "injury"]):
        return "injury"
    if any(word in lower for word in ["fever", "infection", "rash", "chills"]):
        return "infection"
    if any(word in lower for word in ["stomach", "abdomen", "abdominal", "belly", "vomit", "stool"]):
        return "abdominal"
    if any(word in lower for word in ["allergic", "allergy", "anaphylaxis", "throat swelling", "lips swelling"]):
        return "allergic"
    if any(word in lower for word in ["suicidal", "self-harm", "anxiety", "panic"]):
        return "mental_health"
    return "general"


def _split_symptoms(symptoms: str) -> list[str]:
    parts = [part.strip(" .") for part in re.split(r",|;|\band\b", symptoms) if part.strip(" .")]
    return parts or [symptoms.strip()]


def _minimum_level(level: TriageLevel, floor: TriageLevel) -> TriageLevel:
    return LEVEL_ORDER[max(LEVEL_ORDER.index(level), LEVEL_ORDER.index(floor))]


def _base_level(severity: Severity, has_red_flag: bool, pregnant_or_immunocompromised: bool = False) -> TriageLevel:
    if has_red_flag:
        return "emergency"
    if severity == "high":
        return "urgent_care"
    if severity == "moderate":
        return "doctor_visit"
    if pregnant_or_immunocompromised:
        return "doctor_visit"
    return "self_care"


def _next_steps(level: TriageLevel) -> list[str]:
    if level == "emergency":
        return [
            "Call 911 or local emergency services now.",
            "Go to the nearest ER if emergency services are not available.",
            "Do not drive yourself if you feel faint, weak, confused, or short of breath.",
        ]
    if level == "urgent_care":
        return [
            "Seek same-day urgent care evaluation.",
            "Avoid strenuous activity until evaluated.",
            "Escalate to emergency care if symptoms worsen or red flags appear.",
        ]
    if level == "doctor_visit":
        return [
            "Schedule a doctor visit soon.",
            "Track symptom changes and duration.",
            "Seek urgent care if symptoms worsen or become severe.",
        ]
    return [
        "Rest and stay hydrated.",
        "Monitor symptoms for changes.",
        "Contact a clinician if symptoms persist, worsen, or new concerning symptoms appear.",
    ]


def validate_intake_node(state: dict[str, Any]) -> dict[str, Any]:
    _state_append(state, "validate_intake")
    request = state["request"]
    if not isinstance(request, TriageRequest):
        request = TriageRequest.model_validate(request)
    state["request"] = request
    return state


def symptom_analyzer_node(state: dict[str, Any]) -> dict[str, Any]:
    _state_append(state, "symptom_analyzer")
    request: TriageRequest = state["request"]
    red_flags = detect_red_flags(_analysis_text(request))
    state["symptom_analyzer"] = SymptomAnalyzerOutput(
        symptoms_extracted=_split_symptoms(request.symptoms),
        severity_assessment=request.severity,
        duration_assessment=request.duration,
        category=detect_category(request.symptoms),
        red_flags=red_flags,
        red_flag_detected=bool(red_flags),
    )
    return state


def care_guidance_node(state: dict[str, Any]) -> dict[str, Any]:
    _state_append(state, "care_guidance")
    request: TriageRequest = state["request"]
    analyzer: SymptomAnalyzerOutput = state["symptom_analyzer"]
    level = _base_level(request.severity, analyzer.red_flag_detected, request.pregnant_or_immunocompromised)
    state["care_guidance"] = CareGuidanceOutput(
        recommended_level=level,
        reasoning=(
            "Emergency red flags were detected."
            if analyzer.red_flag_detected
            else f"Severity '{request.severity}' maps to {level} using deterministic triage rules."
        ),
        next_steps=_next_steps(level),
    )
    return state


def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    _state_append(state, "supervisor")
    request: TriageRequest = state["request"]
    analyzer: SymptomAnalyzerOutput = state["symptom_analyzer"]
    guidance: CareGuidanceOutput = state["care_guidance"]
    level = guidance.recommended_level
    safety_override = False
    if analyzer.red_flag_detected:
        safety_override = request.severity in {"low", "moderate"} or level != "emergency"
        level = "emergency"
    elif request.severity == "high":
        original = level
        level = _minimum_level(level, "urgent_care")
        safety_override = original != level

    reason = (
        "Red flag symptoms require emergency evaluation."
        if level == "emergency"
        else f"Deterministic triage selected {level} based on severity and available safety context."
    )
    supervisor = SupervisorOutput(
        final_triage_level=level,
        reason=reason,
        next_steps=_next_steps(level),
        safety_note="This is not a diagnosis or a substitute for professional medical care.",
        safety_override_applied=safety_override,
    )
    state["supervisor"] = supervisor
    state["final"] = supervisor
    return state


def fallback_node(state: dict[str, Any]) -> dict[str, Any]:
    _state_append(state, "fallback")
    request: TriageRequest = state["request"]
    red_flags = detect_red_flags(_analysis_text(request))
    analyzer = SymptomAnalyzerOutput(
        symptoms_extracted=_split_symptoms(request.symptoms),
        severity_assessment=request.severity,
        duration_assessment=request.duration,
        category=detect_category(request.symptoms),
        red_flags=red_flags,
        red_flag_detected=bool(red_flags),
    )
    level = _base_level(request.severity, bool(red_flags), request.pregnant_or_immunocompromised)
    guidance = CareGuidanceOutput(
        recommended_level=level,
        reasoning="Deterministic fallback used because the agent path failed.",
        next_steps=_next_steps(level),
    )
    final = SupervisorOutput(
        final_triage_level=level,
        reason=(
            "Red flag symptoms require emergency evaluation."
            if red_flags
            else "Deterministic fallback selected a conservative triage level."
        ),
        next_steps=_next_steps(level),
        safety_note="This is not a diagnosis or a substitute for professional medical care.",
        safety_override_applied=bool(red_flags and request.severity in {"low", "moderate"}),
    )
    state["symptom_analyzer"] = analyzer
    state["care_guidance"] = guidance
    state["supervisor"] = final
    state["final"] = final
    return state


def persist_case_node(state: dict[str, Any]) -> dict[str, Any]:
    _state_append(state, "persist_case")
    state.setdefault("case_id", str(uuid.uuid4()))
    return state


def _response_from_state(state: dict[str, Any]) -> TriageResponse:
    graph = GraphOutput(nodes_visited=state["nodes_visited"], path="→".join(state["nodes_visited"]))
    final: SupervisorOutput = state["final"]
    return TriageResponse(
        case_id=state["case_id"],
        triage_level=final.final_triage_level,
        final=final,
        symptom_analyzer=state["symptom_analyzer"],
        care_guidance=state["care_guidance"],
        supervisor=state["supervisor"],
        graph=graph,
    )


def run_triage_graph(
    request: TriageRequest,
    db_session: object | None = None,
    simulate_llm_failure: bool = False,
) -> TriageResponse:
    del db_session
    state: dict[str, Any] = {"request": request, "nodes_visited": [], "case_id": str(uuid.uuid4())}
    validate_intake_node(state)
    if simulate_llm_failure:
        fallback_node(state)
        persist_case_node(state)
        return _response_from_state(state)
    symptom_analyzer_node(state)
    care_guidance_node(state)
    supervisor_node(state)
    persist_case_node(state)
    return _response_from_state(state)


# Compatibility alias for older local imports.
run_triage = run_triage_graph
