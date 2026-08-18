"""Auth + audit-log middleware (README §11: authentication and audit
logging are required before handling real user studies). One pass over
every request: reject unauthenticated ones when a token is configured, then
record every mutating request to the audit_log table — never edited,
never deleted.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_UNAUTHENTICATED_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}
_MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class AuthAndAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        is_health = request.url.path.endswith("/health")
        if settings.api_auth_token and request.method != "OPTIONS" and not is_health and request.url.path not in _UNAUTHENTICATED_PATHS:
            auth_header = request.headers.get("authorization", "")
            token = auth_header.removeprefix("Bearer ").strip()
            if token != settings.api_auth_token:
                return JSONResponse({"detail": "Missing or invalid API token."}, status_code=401)

        response = await call_next(request)

        if request.method in _MUTATING_METHODS:
            self._log_audit(request, response.status_code)

        return response

    @staticmethod
    def _log_audit(request: Request, status_code: int) -> None:
        # Local import to avoid a hard dependency between core/ and db/ at module load time.
        from app.db.models.audit_log import AuditLog
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            db.add(
                AuditLog(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    client_host=request.client.host if request.client else None,
                )
            )
            db.commit()
        except Exception:  # noqa: BLE001 — auditing must never break the actual request
            logger.exception("Failed to write audit log entry")
        finally:
            db.close()
