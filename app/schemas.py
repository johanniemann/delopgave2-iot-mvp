"""Bounded API inputs. OpenAPI is generated from these contracts."""
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    request_id: UUID


class Command(Input):
    expected_version: int = Field(ge=0)


class NewScenario(Input):
    kind: Literal["fault", "normal", "invalid", "empty"] = "fault"
    title: str | None = Field(default=None, min_length=1, max_length=100)
    prepare: bool = True


class Reading(Command):
    measured_at: AwareDatetime
    value: float | None = None
    signal: Literal["wind_speed"] = "wind_speed"
    unit: Literal["m/s"] = "m/s"
    quality: Literal["Usable", "Invalid"] = "Usable"
    reason: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def classify_quality(self):
        if self.value is None or not 0 <= self.value <= 100:
            self.quality = "Invalid"
            self.reason = "Missing value or outside the synthetic 0-100 m/s range."
        elif self.quality == "Invalid" and not self.reason:
            self.reason = "Reported unusable by the synthetic source."
        return self


class RiskDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_id: Literal["yaw-drive", "pitch-actuator"]
    decision: Literal["Accepted", "Rejected"]


class Review(Command):
    reviewer: str = Field(default="Authenticated specialist", min_length=2, max_length=80,
                          description="Legacy input, ignored by HTTP API; identity comes from the signed-in account.")
    note: str = Field(min_length=3, max_length=1000)
    decisions: list[RiskDecision] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def each_risk_once(self):
        if {d.risk_id for d in self.decisions} != {"yaw-drive", "pitch-actuator"}:
            raise ValueError("Provide one decision for each risk.")
        return self


class Outcome(Command):
    simulated: Literal[True]
    external_reference: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._/-]*$")
    all_work_complete: bool
    verification: Literal["Passed", "Failed"]
    evidence_reference: str = Field(min_length=3, max_length=200)
    note: str = Field(min_length=3, max_length=1000)
