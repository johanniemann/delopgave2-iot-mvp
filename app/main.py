"""HTTP boundary and local dashboard hosting."""
from contextlib import asynccontextmanager
from dataclasses import dataclass
import hmac
import logging
import os
from pathlib import Path
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from psycopg import Error as DatabaseError
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .db import initialize, open_pool
from .domain import DomainError
from .schemas import Command, NewScenario, Outcome, Reading, Review
from .service import Maintenance

logger = logging.getLogger(__name__)
STATIC = Path(__file__).with_name("static")


@dataclass(frozen=True)
class Settings:
    database_url: str
    mode: str = "local"
    api_token: str = ""
    public_origin: str = ""
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    seed_demo: bool = True

    def __post_init__(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL must point to a dedicated PostgreSQL prototype database.")
        if self.mode not in {"local", "shared"}:
            raise ValueError("APP_MODE must be local or shared.")
        if self.mode == "shared" and (len(self.api_token) < 32 or not self.public_origin.startswith("https://")):
            raise ValueError("Shared mode requires a 32+ character API_TOKEN and HTTPS PUBLIC_ORIGIN.")
        if "*" in self.allowed_hosts:
            raise ValueError("Use explicit ALLOWED_HOSTS, not a wildcard.")

    @classmethod
    def from_env(cls):
        return cls(database_url=os.environ.get("DATABASE_URL", ""), mode=os.environ.get("APP_MODE", "local"),
                   api_token=os.environ.get("API_TOKEN", ""), public_origin=os.environ.get("PUBLIC_ORIGIN", ""),
                   allowed_hosts=tuple(h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()),
                   seed_demo=os.environ.get("SEED_DEMO", "true").lower() == "true")


def error_response(code, message, status, headers=None):
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status, headers=headers)


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        pool = open_pool(settings.database_url)
        try:
            initialize(pool)
            app.state.maintenance = Maintenance(pool)
            if settings.seed_demo:
                app.state.maintenance.seed()
            yield
        finally:
            pool.close()

    app = FastAPI(title="Aeris · Predictive Maintenance", version="0.1.0", lifespan=lifespan,
                  description="Synthetic academic prototype. Forecasts and external maintenance outcomes are simulated.",
                  redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
    bearer = HTTPBearer(auto_error=False)
    write_windows = {}

    def authorized(credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
        if settings.mode == "shared":
            if not credentials or not hmac.compare_digest(credentials.credentials.encode(), settings.api_token.encode()):
                raise HTTPException(401, "Enter a valid shared-demo access token.", headers={"WWW-Authenticate": "Bearer"})

    @app.middleware("http")
    async def request_guards(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            expected_origin = settings.public_origin or f"{request.url.scheme}://{request.headers.get('host', '')}"
            if origin and origin != expected_origin:
                return error_response("FOREIGN_ORIGIN", "Cross-origin changes are not allowed.", 403)
            if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
                return error_response("JSON_REQUIRED", "Send an application/json request body.", 415)
            length = request.headers.get("content-length")
            if length is None:
                return error_response("LENGTH_REQUIRED", "A Content-Length is required for bounded JSON writes.", 411)
            if not length.isdigit() or int(length) > 16384:
                return error_response("BODY_TOO_LARGE", "The JSON body must be at most 16 KiB.", 413)
            ip = request.client.host if request.client else "unknown"
            now = monotonic()
            start, count = write_windows.get(ip, (now, 0))
            if now - start >= 60:
                start, count = now, 0
            if count >= 60:
                return error_response("RATE_LIMIT", "Too many changes. Please wait a minute.", 429, {"Retry-After": "60"})
            if len(write_windows) >= 1024 and ip not in write_windows:
                write_windows.pop(next(iter(write_windows)))
            write_windows[ip] = (start, count + 1)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        policy = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path == "/docs":
            # FastAPI's generated Swagger UI uses this CDN and inline initialization.
            policy = policy.replace("script-src 'self'", "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'").replace("style-src 'self'", "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'")
        response.headers["Content-Security-Policy"] = policy
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return error_response(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        fields = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse({"error": {"code": "INVALID_INPUT", "message": "Check the supplied fields.", "fields": fields}}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response("HTTP_ERROR", str(exc.detail), exc.status_code, exc.headers)

    async def database_error(request, exc):
        logger.error("Database request failed (%s)", type(exc).__name__)
        return error_response("DATABASE_UNAVAILABLE", "The database is temporarily unavailable. Please retry.", 503)

    app.add_exception_handler(DatabaseError, database_error)
    app.add_exception_handler(PoolTimeout, database_error)

    def maintenance(request: Request) -> Maintenance:
        return request.app.state.maintenance

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC / "index.html")

    @app.get("/health", tags=["Operations"])
    def health(service: Maintenance = Depends(maintenance)):
        with service.pool.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "database": "connected", "mode": settings.mode, "simulation": True}

    api = APIRouter(prefix="/api", dependencies=[Depends(authorized)], tags=["Predictive Maintenance"])

    @api.get("/overview")
    def overview(service: Maintenance = Depends(maintenance)):
        return service.overview()

    @api.get("/scenarios/{scenario_id}")
    def detail(scenario_id: UUID, service: Maintenance = Depends(maintenance)):
        return service.detail(scenario_id)

    @api.get("/cases/{case_id}")
    def case_detail(case_id: str, service: Maintenance = Depends(maintenance)):
        return service.case_detail(case_id)

    @api.post("/scenarios", status_code=201)
    def new_scenario(command: NewScenario, service: Maintenance = Depends(maintenance)):
        return service.create_scenario(command)

    @api.post("/scenarios/{scenario_id}/readings", status_code=201)
    def reading(scenario_id: UUID, command: Reading, service: Maintenance = Depends(maintenance)):
        return service.record_reading(scenario_id, command)

    @api.post("/scenarios/{scenario_id}/assess")
    def assess(scenario_id: UUID, command: Command, service: Maintenance = Depends(maintenance)):
        return service.assess(scenario_id, command)

    @api.post("/scenarios/{scenario_id}/forecast")
    def forecast(scenario_id: UUID, command: Command, service: Maintenance = Depends(maintenance)):
        return service.forecast(scenario_id, command)

    @api.put("/scenarios/{scenario_id}/review")
    def review(scenario_id: UUID, command: Review, service: Maintenance = Depends(maintenance)):
        return service.review(scenario_id, command)

    @api.post("/scenarios/{scenario_id}/case", status_code=201)
    def create_case(scenario_id: UUID, command: Command, service: Maintenance = Depends(maintenance)):
        return service.create_case(scenario_id, command)

    @api.post("/cases/{case_id}/outcomes")
    def outcome(case_id: str, command: Outcome, service: Maintenance = Depends(maintenance)):
        return service.record_outcome(case_id, command)

    app.include_router(api)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
