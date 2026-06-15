"""Minimal Zero Trust middleware: deny-by-default identity verification.

Every request is untrusted until verified. The MVP checks for an identity
header (a stand-in for phishing-resistant auth / mTLS / SMART context). Public
probe paths are explicitly allow-listed. Production swaps the header check for
real OIDC / workload identity (see docs/zero-trust-model.md).
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_PUBLIC_PATHS = {"/healthz", "/docs", "/openapi.json", "/redoc"}


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, require_identity: bool = True) -> None:
        super().__init__(app)
        self.require_identity = require_identity

    async def dispatch(self, request: Request, call_next):
        if not self.require_identity or request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        identity = request.headers.get("x-florence-identity")
        role = request.headers.get("x-florence-role")
        if not identity or not role:
            return JSONResponse(
                status_code=401,
                content={"detail": "Zero Trust: missing verified identity/role (deny-by-default)."},
            )
        request.state.identity = identity
        request.state.role = role
        return await call_next(request)
