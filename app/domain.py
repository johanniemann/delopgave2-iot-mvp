"""Small domain rules, independent of HTTP and PostgreSQL."""
from dataclasses import dataclass
from typing import Any

DEMO_THRESHOLD = 28.0
MODEL_VERSION = "illustrated-forecast-v1"


@dataclass
class DomainError(Exception):
    code: str
    message: str
    status: int = 409


def current_fault(readings: list[dict[str, Any]]) -> dict[str, Any] | None:
    usable = [r for r in readings if r["quality"] == "Usable" and r["value"] is not None]
    triggered = [r for r in usable if r["value"] > DEMO_THRESHOLD]
    if not triggered:
        return None
    return {
        "peak": max(r["value"] for r in triggered),
        "threshold": DEMO_THRESHOLD,
        "evidence": [str(r["id"]) for r in triggered],
        "code": "DEMO-HIGH-WIND",
        "summary": "Wind speed exceeded the illustrative 28.0 m/s rule.",
    }


def simulated_risks() -> list[dict[str, Any]]:
    # Fixed presentation fixtures. These are NOT computed probabilities or ML output.
    return [
        {"id": "yaw-drive", "label": "Yaw drive stress", "component": "Yaw system",
         "likelihood": 0.72, "horizon_days": 14,
         "explanation": "Illustrative follow-up risk after the demo wind event. No model analysis was performed."},
        {"id": "pitch-actuator", "label": "Pitch actuator wear", "component": "Pitch system",
         "likelihood": 0.38, "horizon_days": 30,
         "explanation": "A second fixed example for the specialist to accept or reject. Not a measured failure probability."},
    ]


def require_case_gate(incident: dict | None, forecast: dict | None) -> None:
    if not incident:
        raise DomainError("INCIDENT_REQUIRED", "A current fault incident is required before a case can be created.")
    if not forecast or forecast["review_status"] != "Reviewed":
        raise DomainError("REVIEW_REQUIRED", "Review the failure forecast before creating a predictive case.")


def resolves_case(all_work_complete: bool, verification: str) -> bool:
    return all_work_complete and verification == "Passed"
