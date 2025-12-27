"""
JWT Authentication Module for ToastyAnalytics

Provides token-based authentication for API endpoints.
Supports user authentication, API key management, and role-based access control.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """JWT token payload data"""

    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []
    scopes: list[str] = []


class Token(BaseModel):
    """Token response model"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class AuthManager:
    """Manages authentication and authorization"""

    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = ALGORITHM):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = pwd_context

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data to encode in the token
            expires_delta: Token expiration time (default: 30 minutes)

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token.

        Args:
            data: Payload data to encode in the token
            expires_delta: Token expiration time (default: 7 days)

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and verify a JWT token.

        Args:
            token: The JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
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

    def create_token_pair(self, user_data: Dict[str, Any]) -> Token:
        """
        Create both access and refresh tokens.

        Args:
            user_data: User data to encode in tokens

        Returns:
            Token object with both access and refresh tokens
        """
        access_token = self.create_access_token(user_data)
        refresh_token = self.create_refresh_token({"user_id": user_data.get("user_id")})

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


# Global auth manager instance
auth_manager = AuthManager()


# FastAPI Dependencies


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    token = credentials.credentials
    payload = auth_manager.decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
        )

    return TokenData(
        user_id=user_id,
        username=payload.get("username"),
        email=payload.get("email"),
        roles=payload.get("roles", []),
        scopes=payload.get("scopes", []),
    )


async def require_role(required_role: str):
    """
    FastAPI dependency to require a specific role.

    Usage:
        @app.get("/admin")
        async def admin_route(user: TokenData = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """

    async def role_checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user

    return role_checker


async def require_scope(required_scope: str):
    """
    FastAPI dependency to require a specific scope/permission.

    Usage:
        @app.post("/grade")
        async def grade_code(
            user: TokenData = Depends(require_scope("grade:write"))
        ):
            return {"message": "Grading allowed"}
    """

    async def scope_checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if required_scope not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required",
            )
        return user

    return scope_checker


# API Key Management


class APIKeyManager:
    """Manages API keys for service-to-service authentication"""

    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self._load_api_keys()

    def _load_api_keys(self):
        """Load API keys from environment or database"""
        # In production, load from database
        # For now, load from environment
        default_key = os.getenv("API_KEY")
        if default_key:
            self.api_keys[default_key] = {
                "name": "default",
                "scopes": ["*"],
                "created_at": datetime.utcnow(),
            }

    def verify_api_key(self, api_key: str) -> bool:
        """Verify if an API key is valid"""
        return api_key in self.api_keys

    def get_api_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get information about an API key"""
        return self.api_keys.get(api_key)

    def create_api_key(self, name: str, scopes: list[str]) -> str:
        """Create a new API key"""
        import secrets

        api_key = f"ta_{secrets.token_urlsafe(32)}"

        self.api_keys[api_key] = {
            "name": name,
            "scopes": scopes,
            "created_at": datetime.utcnow(),
        }

        return api_key

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            return True
        return False


# Global API key manager
api_key_manager = APIKeyManager()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify API key authentication.

    Usage:
        @app.get("/api/data")
        async def get_data(api_key_info = Depends(verify_api_key)):
            return {"data": "sensitive information"}
    """
    api_key = credentials.credentials

    if not api_key_manager.verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    key_info = api_key_manager.get_api_key_info(api_key)
    if key_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return key_info
