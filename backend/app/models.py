from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    symptoms: Mapped[str] = mapped_column(Text)
    duration: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20))
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    pregnant_or_immunocompromised: Mapped[bool] = mapped_column(Boolean, default=False)
    triage_level: Mapped[str] = mapped_column(String(30))
    final_recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent_output: Mapped["AgentOutput"] = relationship(back_populates="case", uselist=False)


class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(40), ForeignKey("cases.case_id"), unique=True, index=True)
    symptom_analyzer_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    care_guidance_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    supervisor_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    graph_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="agent_output")

