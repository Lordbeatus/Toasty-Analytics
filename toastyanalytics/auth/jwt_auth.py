"""JWT and API-key authentication for the HTTP API.

Two credential types are supported:

* **API keys** (``X-API-Key``) identify a service or long-lived client and are
  configured with ``TOASTY_API_KEYS``.
* **JWTs** (``Authorization: Bearer``) are short-lived tokens minted by
  ``POST /auth/token`` from a valid API key.

Both resolve to a :class:`TokenData` carrying roles and scopes, which route
dependencies check with :func:`require_scope` and :func:`require_role`.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from toastyanalytics.config import config

ISSUER = "toastyanalytics"

SCOPE_GRADE_READ = "grade:read"
SCOPE_GRADE_WRITE = "grade:write"
SCOPE_ANALYTICS_READ = "analytics:read"
SCOPE_TOKEN_ISSUE = "token:issue"
KNOWN_SCOPES = {
    SCOPE_GRADE_READ,
    SCOPE_GRADE_WRITE,
    SCOPE_ANALYTICS_READ,
    SCOPE_TOKEN_ISSUE,
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name=config.API_KEY_HEADER, auto_error=False)


class TokenData(BaseModel):
    """Authenticated caller identity."""

    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    auth_type: str = "jwt"


class Token(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


@dataclass(frozen=True)
class APIKeyRecord:
    """A configured API key and the identity it represents."""

    name: str
    user_id: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]

    def allows(self, scope: str) -> bool:
        return "*" in self.scopes or scope in self.scopes


def parse_api_keys(spec: Optional[str]) -> Dict[str, APIKeyRecord]:
    """
    Parse ``TOASTY_API_KEYS`` into records.

    Format: ``key:user_id:roles:scopes`` with entries separated by commas,
    roles by ``|``, and scopes by ``|``. Example::

        dev-key:local:admin:*
        ci-key:ci-runner::grade:read|analytics:read
    """
    records: Dict[str, APIKeyRecord] = {}
    if not spec:
        return records

    for raw_entry in spec.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        parts = entry.split(":", 3)
        if len(parts) != 4:
            raise ValueError(
                "Invalid TOASTY_API_KEYS entry; expected key:user:roles:scopes"
            )
        key, user_id, roles_raw, scopes_raw = parts
        key = key.strip()
        if not key:
            raise ValueError("TOASTY_API_KEYS contains an empty key")

        roles = tuple(role for role in roles_raw.split("|") if role)
        scopes = tuple(scope for scope in scopes_raw.split("|") if scope)
        unknown = set(scopes) - {"*"} - KNOWN_SCOPES
        if unknown:
            raise ValueError(
                "Unknown scope(s) in TOASTY_API_KEYS: " + ", ".join(sorted(unknown))
            )

        records[key] = APIKeyRecord(
            name=f"key-{len(records) + 1}",
            user_id=user_id or "service",
            roles=roles,
            scopes=scopes,
        )

    return records


class AuthManager:
    """Creates and verifies JWT access and refresh tokens."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        access_ttl_minutes: Optional[int] = None,
        refresh_ttl_days: Optional[int] = None,
    ):
        self.secret_key = config.JWT_SECRET_KEY if secret_key is None else secret_key
        self.algorithm = algorithm or config.JWT_ALGORITHM
        self.access_ttl = timedelta(
            minutes=access_ttl_minutes or config.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self.refresh_ttl = timedelta(
            days=refresh_ttl_days or config.REFRESH_TOKEN_EXPIRE_DAYS
        )
        self.pwd_context = pwd_context

    @property
    def configured(self) -> bool:
        return bool(self.secret_key)

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def _encode(
        self,
        user_id: str,
        scopes: List[str],
        roles: List[str],
        token_type: str,
        ttl: timedelta,
    ) -> str:
        if not self.secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT_SECRET_KEY is not configured",
            )
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "user_id": user_id,
            "scopes": scopes,
            "roles": roles,
            "type": token_type,
            "iss": ISSUER,
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
    ) -> str:
        return self._encode(
            user_id, scopes or [], roles or [], "access", self.access_ttl
        )

    def create_refresh_token(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
    ) -> str:
        return self._encode(
            user_id, scopes or [], roles or [], "refresh", self.refresh_ttl
        )

    def create_token_pair(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
    ) -> Token:
        scopes = scopes or []
        roles = roles or []
        return Token(
            access_token=self.create_access_token(user_id, scopes, roles),
            refresh_token=self.create_refresh_token(user_id, scopes, roles),
            token_type="bearer",
            expires_in=int(self.access_ttl.total_seconds()),
        )

    def decode_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        """Decode a token, raising 401 for invalid, expired, or wrong-type tokens."""
        if not self.secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT_SECRET_KEY is not configured",
            )
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=ISSUER,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Expected a {expected_type} token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload


auth_manager = AuthManager()
api_keys: Dict[str, APIKeyRecord] = parse_api_keys(config.API_KEYS)


def is_auth_configured() -> bool:
    return auth_manager.configured or bool(api_keys)


def principal_from_api_key(api_key: str) -> Optional[TokenData]:
    """Resolve an API key to a principal in constant time."""
    for candidate, record in api_keys.items():
        if secrets.compare_digest(candidate, api_key):
            return TokenData(
                user_id=record.user_id,
                roles=list(record.roles),
                scopes=list(record.scopes),
                auth_type="api_key",
            )
    return None


def authenticate_headers(
    authorization: Optional[str], api_key: Optional[str]
) -> Optional[TokenData]:
    """
    Resolve credentials from headers without raising.

    Used by the rate limiter to find a caller tier before route dependencies run.
    Returns ``None`` for missing or invalid credentials.
    """
    if not config.AUTH_ENABLED:
        return TokenData(
            user_id="anonymous",
            roles=["admin"],
            scopes=["*"],
            auth_type="disabled",
        )

    if api_key:
        principal = principal_from_api_key(api_key)
        if principal:
            return principal

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = auth_manager.decode_token(token)
        except HTTPException:
            return None
        return TokenData(
            user_id=payload["sub"],
            username=payload.get("username"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
            scopes=payload.get("scopes", []),
            auth_type="jwt",
        )

    return None


async def get_principal(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_scheme),
) -> TokenData:
    """Resolve the caller from a bearer token or API key."""
    if not config.AUTH_ENABLED:
        return TokenData(
            user_id="anonymous",
            roles=["admin"],
            scopes=["*"],
            auth_type="disabled",
        )

    if not is_auth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Authentication is enabled but not configured. "
                "Set JWT_SECRET_KEY and TOASTY_API_KEYS."
            ),
        )

    if bearer and bearer.credentials:
        payload = auth_manager.decode_token(bearer.credentials)
        return TokenData(
            user_id=payload["sub"],
            username=payload.get("username"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
            scopes=payload.get("scopes", []),
            auth_type="jwt",
        )

    if api_key:
        principal = principal_from_api_key(api_key)
        if principal:
            return principal
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(scope: str):
    """Dependency factory requiring ``scope`` (``*`` grants everything)."""

    async def scope_checker(
        principal: TokenData = Depends(get_principal),
    ) -> TokenData:
        if "*" in principal.scopes or scope in principal.scopes:
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope '{scope}' required",
        )

    return scope_checker


def require_role(role: str):
    """Dependency factory requiring ``role``."""

    async def role_checker(principal: TokenData = Depends(get_principal)) -> TokenData:
        if role in principal.roles:
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' required",
        )

    return role_checker


def get_current_user(principal: TokenData = Depends(get_principal)) -> TokenData:
    """Backward-compatible alias for :func:`get_principal`."""
    return principal


__all__ = [
    "APIKeyRecord",
    "AuthManager",
    "SCOPE_ANALYTICS_READ",
    "SCOPE_GRADE_READ",
    "SCOPE_GRADE_WRITE",
    "SCOPE_TOKEN_ISSUE",
    "Token",
    "TokenData",
    "api_key_scheme",
    "api_keys",
    "auth_manager",
    "authenticate_headers",
    "get_current_user",
    "get_principal",
    "is_auth_configured",
    "parse_api_keys",
    "principal_from_api_key",
    "require_role",
    "require_scope",
]
