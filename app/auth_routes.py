"""Cookie authentication and role dependencies shared by every protected route."""
import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import APIKeyCookie

from .accounts import ChangePassword, Login, NewUser, ResetPassword, UpdateUser
from .domain import DomainError


def build_auth(settings):
    cookie_name = "__Host-aeris-session" if settings.mode == "shared" else "aeris-local-" + settings.cookie_namespace
    cookie = APIKeyCookie(name=cookie_name, auto_error=False)
    safe_methods = {"GET", "HEAD", "OPTIONS"}

    def current(request: Request, token=Depends(cookie)):
        session = request.app.state.accounts.session(token)
        if request.method not in safe_methods:
            csrf = request.headers.get("x-csrf-token", "")
            if not hmac.compare_digest(csrf.encode(), session["csrf_token"].encode()):
                raise DomainError("CSRF_REQUIRED", "Refresh your session before making changes.", 403)
        return session

    def member(session=Depends(current)):
        if session["user"]["must_change_password"]:
            raise DomainError("PASSWORD_CHANGE_REQUIRED", "Change your temporary password before opening the workspace.", 403)
        return session

    def admin(session=Depends(member)):
        if session["user"]["role"] != "admin":
            raise DomainError("ADMIN_REQUIRED", "Administrator access is required.", 403)
        return session

    router = APIRouter(prefix="/api/auth", tags=["Accounts"])

    def clear(response):
        response.delete_cookie(cookie_name, path="/", secure=settings.mode == "shared", httponly=True, samesite="strict")

    @router.post("/login")
    def login(command: Login, request: Request, response: Response):
        old = request.cookies.get(cookie_name)
        # Successful login always issues a fresh opaque session identifier.
        token, result = request.app.state.accounts.login(command, request.client.host if request.client else "unknown")
        if old:
            from .accounts import digest
            request.app.state.accounts.logout({"session_hash": digest(old)})
        response.set_cookie(cookie_name, token, max_age=8*60*60, httponly=True,
                            secure=settings.mode == "shared", samesite="strict", path="/")
        return result

    @router.get("/me")
    def me(session=Depends(current)):
        return {key: session[key] for key in ("user", "csrf_token", "expires_at")}

    @router.post("/logout")
    def logout(request: Request, response: Response, session=Depends(current)):
        request.app.state.accounts.logout(session)
        clear(response)
        return {"signed_out": True}

    @router.post("/password")
    def password(command: ChangePassword, request: Request, response: Response, session=Depends(current)):
        request.app.state.accounts.change_password(session, command)
        clear(response)
        return {"signed_out": True, "message": "Password changed. Sign in again."}

    management = APIRouter(prefix="/api/admin", tags=["Administration"], dependencies=[Depends(admin)])

    @management.get("/users")
    def users(request: Request):
        return {"users": request.app.state.accounts.list_users()}

    @management.post("/users", status_code=201)
    def create(command: NewUser, request: Request, session=Depends(admin)):
        return request.app.state.accounts.create_user(session, command)

    @management.patch("/users/{user_id}")
    def update(user_id: UUID, command: UpdateUser, request: Request, session=Depends(admin)):
        return request.app.state.accounts.update_user(session, user_id, command)

    @management.post("/users/{user_id}/password")
    def reset(user_id: UUID, command: ResetPassword, request: Request, session=Depends(admin)):
        request.app.state.accounts.reset_password(session, user_id, command)
        return {"password_reset_required": True}

    @management.get("/audit")
    def audit(request: Request):
        return {"events": request.app.state.accounts.audit()}

    return router, management, member
