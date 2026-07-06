"""
Security headers middleware.

Adds standard defensive HTTP response headers. None of these require any
external service or configuration; they are static, well-known mitigations
for common browser-side vulnerability classes (clickjacking, MIME-sniffing,
referrer leakage).
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
