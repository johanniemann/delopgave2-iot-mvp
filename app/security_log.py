"""Bounded security events to container stderr; never copy request input."""
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger("aeris.security")


def record_rejection(request, status: int) -> None:
    if status not in {401, 403, 429} or not request.url.path.startswith("/api/"):
        return
    route = getattr(request.scope.get("route"), "path", "/api/unmatched")
    event = "rate_limited" if status == 429 else "access_denied"
    if route == "/api/auth/login" and status == 401:
        event = "login_failed"
    # No URL/query, peer IP, username, headers, body, cookie or token is recorded.
    method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"} else "OTHER"
    entry = {"time": datetime.now(timezone.utc).isoformat(), "event": event,
             "method": method, "route": route, "status": status}
    actor = getattr(request.state, "actor_id", None)
    if actor is not None:
        entry["actor_id"] = actor
    logger.warning(json.dumps(entry, separators=(",", ":")))
