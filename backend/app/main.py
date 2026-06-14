from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import CaseDetail, CaseSummary, LoginRequest, LoginResponse, TriageRequest, TriageResponse
from app.triage_graph import run_triage_graph


app = FastAPI(title="Deterministic Multi-Agent Symptom Triage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CASE_STORE: dict[str, CaseDetail] = {}
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "change-me"
FAKE_TOKEN = "fake-admin-token"


def require_admin(authorization: Annotated[str | None, Header()] = None) -> str:
    if authorization != f"Bearer {FAKE_TOKEN}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return ADMIN_USERNAME


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def auth_login(payload: LoginRequest) -> LoginResponse:
    if payload.username != ADMIN_USERNAME or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(access_token=FAKE_TOKEN)


@app.post("/triage/analyze", response_model=TriageResponse)
def analyze_triage(
    payload: TriageRequest,
    simulate_llm_failure: bool = Query(False),
) -> TriageResponse:
    response = run_triage_graph(payload, db_session=None, simulate_llm_failure=simulate_llm_failure)
    CASE_STORE[response.case_id] = CaseDetail(
        case_id=response.case_id,
        age=payload.age,
        symptoms=payload.symptoms,
        duration=payload.duration,
        severity=payload.severity,
        triage_level=response.triage_level,
        final=response.final,
        symptom_analyzer=response.symptom_analyzer,
        care_guidance=response.care_guidance,
        supervisor=response.supervisor,
        graph=response.graph,
    )
    return response


@app.get("/cases", response_model=list[CaseSummary])
def list_cases(_: str = Depends(require_admin)) -> list[CaseSummary]:
    return [
        CaseSummary(
            case_id=case.case_id,
            age=case.age,
            symptoms=case.symptoms,
            duration=case.duration,
            severity=case.severity,
            triage_level=case.triage_level,
        )
        for case in CASE_STORE.values()
    ]


@app.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, _: str = Depends(require_admin)) -> CaseDetail:
    try:
        return CASE_STORE[case_id]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
