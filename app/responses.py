"""Public maintenance responses, independent of persistence and account records."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, PlainSerializer


# Keep the existing ISO 8601 offset form, including +00:00 rather than changing
# stored evidence to Pydantic's default Z representation in HTTP responses.
Timestamp = Annotated[
    AwareDatetime,
    PlainSerializer(lambda value: value.isoformat(), return_type=str, when_used="json"),
    Field(json_schema_extra={"format": "date-time"}),
]
Quality = Literal["Usable", "Invalid"]
ReviewStatus = Literal["Pending", "Reviewed"]
CaseStatus = Literal["Open", "Resolved"]


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class HealthResponse(Response):
    status: Literal["ok"]
    database: Literal["connected"]
    mode: Literal["local", "shared"]
    simulation: Literal[True]
    revision: str


class Scenario(Response):
    id: UUID
    turbine_id: str
    title: str
    kind: Literal["fault", "normal", "invalid", "empty"]
    created_at: Timestamp
    version: int = Field(ge=0)
    source: str
    fault_assessed_at: Timestamp | None


class SensorReading(Response):
    id: UUID
    scenario_id: UUID
    measured_at: Timestamp
    signal: Literal["wind_speed"]
    value: float | None
    unit: Literal["m/s"]
    quality: Quality
    reason: str


class Incident(Response):
    id: str
    scenario_id: UUID
    detected_at: Timestamp
    peak: float
    threshold: float
    code: str
    summary: str
    evidence: list[UUID]


class ForecastRisk(Response):
    id: Literal["yaw-drive", "pitch-actuator"]
    label: str
    component: str
    likelihood: float = Field(ge=0, le=1)
    horizon_days: int = Field(ge=0)
    explanation: str


class RiskReviewDecision(Response):
    risk_id: Literal["yaw-drive", "pitch-actuator"]
    decision: Literal["Accepted", "Rejected"]


class ForecastReview(Response):
    reviewer: str
    # Seeded historical reviews have no account UUID; authenticated reviews do.
    reviewer_id: UUID | None
    note: str
    decisions: list[RiskReviewDecision]
    reviewed_at: Timestamp


class Forecast(Response):
    id: str
    scenario_id: UUID
    generated_at: Timestamp
    model_version: str
    risks: list[ForecastRisk]
    source_reading_ids: list[UUID]
    review_status: ReviewStatus
    review: ForecastReview | None


class PredictiveCase(Response):
    id: str
    scenario_id: UUID
    incident_id: str
    forecast_id: str
    status: CaseStatus
    created_at: Timestamp
    resolved_at: Timestamp | None
    accepted_risks: list[ForecastRisk]


class MaintenanceOutcome(Response):
    id: UUID
    case_id: str
    external_reference: str
    all_work_complete: bool
    verification: Literal["Passed", "Failed"]
    evidence_reference: str
    note: str
    created_at: Timestamp
    simulated: Literal[True]


class DomainEvent(Response):
    id: UUID
    position: int
    scenario_id: UUID
    name: str
    occurred_at: Timestamp
    # Each event has its own completed-fact payload. It is not an account record
    # or a second, inferred response contract for every individual event name.
    payload: dict[str, JsonValue]


class ScenarioDetailResponse(Response):
    scenario: Scenario
    readings: list[SensorReading]
    incident: Incident | None
    forecast: Forecast | None
    case: PredictiveCase | None
    events: list[DomainEvent]
    outcomes: list[MaintenanceOutcome]


class ScenarioSummary(Scenario):
    incident_id: str | None
    peak: float | None
    forecast_id: str | None
    review_status: ReviewStatus | None
    case_id: str | None
    case_status: CaseStatus | None
    reading_count: int = Field(ge=0)
    usable_count: int = Field(ge=0)


class CaseSummary(PredictiveCase):
    turbine_id: str
    title: str
    source: str


class RecentEvent(DomainEvent):
    title: str
    turbine_id: str


class OverviewMetrics(Response):
    alerts: int = Field(ge=0)
    pending_reviews: int = Field(ge=0)
    open_cases: int = Field(ge=0)
    total_readings: int = Field(ge=0)


class DemoRule(Response):
    signal: Literal["wind_speed"]
    threshold: float
    unit: Literal["m/s"]
    comparison: Literal[">"]
    synthetic: Literal[True]


class OverviewResponse(Response):
    scenarios: list[ScenarioSummary]
    cases: list[CaseSummary]
    metrics: OverviewMetrics
    events: list[RecentEvent]
    rule: DemoRule
    active_scenario_id: UUID | None
    simulation: Literal[True]
    turbine_id: str


class ScenarioCreatedReceipt(Response):
    scenario_id: UUID
    version: int = Field(ge=1)


class ReadingReceipt(ScenarioCreatedReceipt):
    reading_id: UUID
    quality: Quality


class AssessmentReceipt(ScenarioCreatedReceipt):
    # A completed assessment can find no fault, in which case null is explicit.
    incident_id: str | None


class ForecastReceipt(ScenarioCreatedReceipt):
    forecast_id: str


class ReviewReceipt(ForecastReceipt):
    review_status: Literal["Reviewed"]


class CaseReceipt(ScenarioCreatedReceipt):
    case_id: str


class OutcomeReceipt(CaseReceipt):
    status: CaseStatus
    outcome_id: UUID


class InvalidField(Response):
    field: str
    message: str


class ErrorDetail(Response):
    code: str
    message: str
    # Only validation errors include fields. JSONResponse error handlers keep
    # that field absent for ordinary authentication/domain/availability errors.
    fields: list[InvalidField] | None = None


class ErrorResponse(Response):
    error: ErrorDetail
