from fastapi import FastAPI, Depends, Body, HTTPException
from fastapi.responses import JSONResponse
from auth import create_token, verify_token, require_role, USERS
from rate_limiter import is_allowed
from pii import redact

app = FastAPI(
    title="API Security Gateway",
    description="FastAPI middleware pipeline: JWT auth → role check → Redis rate limiter → PII redactor → protected endpoint.",
    version="1.0.0",
)


@app.post("/login")
def login(username: str = Body(...), password: str = Body(...)):
    """Authenticate a user and return a JWT access token.

    Accepts username + password in request body.
    Returns a signed JWT containing the user's identity and role.
    """
    user = USERS.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(username, user["role"])
    return {"access_token": token, "token_type": "bearer"}


@app.post("/protected-resource")
def protected_resource(
    payload: dict = Body(...),
    user: dict = Depends(require_role("user")),
):
    """Protected endpoint demonstrating the full security pipeline.

    Order of operations:
      1. JWT auth (via Depends → verify_token) — rejects 401 if invalid
      2. Role check (via require_role) — rejects 403 if insufficient role
      3. Rate limit check (manual, needs client_id from token) — rejects 429
      4. PII redaction on request body text — sanitizes before processing
    """
    client_id = user["sub"]

    if not is_allowed(client_id):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Try again later."},
        )

    clean_text = redact(payload.get("text", ""))

    return {
        "message": f"Hello {client_id}, request processed.",
        "sanitized_input": clean_text,
    }


@app.get("/health")
def health():
    """Simple health check endpoint."""
    return {"status": "healthy"}
