import jwt
import time
import os
from dotenv import load_dotenv
from fastapi import Header, HTTPException, Depends

# Load environment variables from .env file (local dev only)
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"

# fake user "database" for demo purposes
USERS = {
    "alice": {"password": "adminpass", "role": "admin"},
    "bob": {"password": "userpass", "role": "user"},
}


def create_token(username: str, role: str) -> str:
    """Create a signed JWT containing username, role, and 1-hour expiry."""
    payload = {
        "sub": username,
        "role": role,
        "exp": time.time() + 3600,  # 1 hour expiry
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(authorization: str = Header(...)) -> dict:
    """Extract and validate JWT from the Authorization header.

    Expects header format: "Bearer <token>"
    Returns the decoded payload dict on success.
    Raises 401 if the token is missing, malformed, or expired.
    jwt.decode() validates expiry and signature automatically.
    """
    try:
        if not authorization:
            raise ValueError("Missing authorization header")
        scheme, token = authorization.split(maxsplit=1)
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(required_role: str):
    """Dependency factory for role-based access control.

    Usage: Depends(require_role("user")) on any route.
    Admin role has access to everything.
    Returns the authenticated user dict if the role check passes.
    """
    def checker(user: dict = Depends(verify_token)):
        if user["role"] != required_role and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return checker
