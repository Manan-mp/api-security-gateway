# API Security Gateway - Security Review Findings

## FIXED ✓

### 1. Hardcoded JWT Secret Key
**Location:** `auth.py` (previously)  
**Issue:** `SECRET_KEY = "super-secret-key"` was exposed in source code  
**Fix Applied:**
- Created `.env` file with `SECRET_KEY=dev-secret-key-change-in-production`
- Added `python-dotenv` to requirements.txt
- Updated `auth.py` to load via `load_dotenv()` and raise error if not set
- Updated `docker-compose.yml` to pass `SECRET_KEY` env var
- `.env` already in `.gitignore` (safe from accidental commits)

---

## OTHER SECURITY ISSUES FOUND (Not Fixed — Review for Interview)

### 1. Hardcoded Demo User Credentials ⚠️
**Location:** `auth.py`, lines 13-17  
**Severity:** Medium (demo only)
```python
USERS = {
    "alice": {"password": "adminpass", "role": "admin"},
    "bob": {"password": "userpass", "role": "user"},
}
```

**Interview Answer:**
"This is intentionally a demo project, so I kept authentication simple with hardcoded credentials. In a production system, I would **never** store plaintext passwords in code. Instead:

1. **Password Hashing (bcrypt/Argon2):** Hash passwords using bcrypt before storing them. When a user logs in, hash their input and compare hashes—never store plaintext.
   ```python
   # Production way (not in this code)
   import bcrypt
   hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   # Store hashed, never the original
   ```

2. **External Identity Provider:** Use OAuth2 or OpenID Connect (Auth0, Google Sign-In, GitHub). Let a third party manage users.

3. **Separate Credentials Storage:** Use a secure database with encryption, access controls, and audit logs.

**Why it matters:** If someone gets the code, they have all passwords. This is why we separate secrets (moved SECRET_KEY to .env) and why production systems never embed credentials in code."

---

### 2. Missing Password Hashing ⚠️
**Location:** `main.py` line 18; `auth.py` line 16  
**Issue:** Password comparison is plaintext (`user["password"] != password`)

**Interview Answer:**
"Right now passwords are stored and compared as plaintext. This is only acceptable in this demo because it's not real data. In production:

1. **Hash on Registration:** When a user creates an account, hash their password with bcrypt/Argon2 and store only the hash.
2. **Hash on Login:** When they log in, hash their input and compare to the stored hash. Even I (the developer) shouldn't know the actual password.
3. **Never Log Passwords:** Never print, store in logs, or transmit plaintext passwords.

**Example:**
```python
# Bad (what this demo does)
if user['password'] == input_password:  # Both plaintext!
    login_successful()

# Good (production)
if bcrypt.checkpw(input_password.encode(), user['hashed_password']):
    login_successful()
```

This is fundamental: the app should never handle the actual password, only cryptographic hashes of it."

---

### 3. Weak JWT Algorithm Validation ⚠️
**Location:** `auth.py` line 10  
**Current:** `ALGORITHM = "HS256"` (HMAC-SHA256, symmetric key)

**Interview Answer:**
"This code uses HS256, which is symmetric encryption—the same SECRET_KEY signs and verifies tokens. This is a trade-off:

**HS256 Pros:**
- Simple to implement
- Works well for monolithic apps where one service handles both signing and verification
- Fast
- Good enough for many small projects

**HS256 Cons:**
- If the SECRET_KEY leaks, someone can forge any token
- All services need the same secret to verify tokens

**RS256 (Better for larger systems):**
- Uses public/private key pairs (asymmetric encryption)
- The service signs tokens with a **private key** (kept secret)
- Other services verify with just the **public key** (can be public)
- Even if public key is exposed, tokens can't be forged
- Better for microservices where multiple services need to verify tokens

**My choice for this demo:** HS256 is fine because it's a single service. For production with multiple microservices, I'd use RS256.

**Interview answer:** 'I chose HS256 for simplicity in this small project. In a larger system with multiple services, I'd switch to RS256 to ensure that if one service is compromised, the private key isn't exposed everywhere.'"

---

### 4. Logging Instead of Print ⚠️
**Location:** `rate_limiter.py` line 75  
```python
print(f"Redis error in rate limiter: {e}")
```

**Interview Answer:**
"I used `print()` for debugging, which is fine for quick testing but not production-ready. In production:

1. **Use the `logging` module:** It provides proper log levels (DEBUG, INFO, WARNING, ERROR).
2. **Structured logs:** Can route to log aggregators (ELK, Splunk, CloudWatch) for monitoring.
3. **Security:** Sensitive data (tokens, errors) might leak in logs. With proper logging, you can redact PII and choose what severity to log.

**Example fix (production):**
```python
import logging
logger = logging.getLogger(__name__)

try:
    result = RATE_LIMIT_SCRIPT(...)
except RedisError as e:
    logger.warning(f"Redis error in rate limiter, failing closed")  # Don't include error details in logs
    return False
```

**Why:** Print goes to stdout and is hard to filter/control. Logging is the standard for production apps because it's configurable, can be monitored, and integrates with monitoring tools."

---

### 5. Rate Limiter Uses Client Username as Key ⚠️
**Location:** `main.py` line 38: `client_id = user["sub"]`  
**Then:** Passed to `is_allowed(client_id)` in `rate_limiter.py`

**Interview Answer:**
"Right now, rate limits are per username. This means:
- If 'bob' logs in and makes 5 requests, he's limited
- If 'bob' logs in again (new session), he shares the same bucket with his old session
- All requests from 'bob' across all sessions count toward the same limit

**For a demo, this is fine.** But in production:

1. **Per-Token Limits:** Rate limit per JWT token (add a JTI—JWT ID claim).
   ```python
   # In token creation
   \"jti\": str(uuid.uuid4()),  # Unique ID per token
   ```
   Then rate-limit by jti, not username. This gives each session its own bucket.

2. **Per-IP Limits:** Rate limit by IP address to prevent distributed attacks.

3. **Tiered Limits:** Different limits for different users (free vs premium).

**My approach in this demo:** Per-username is simpler and works to demonstrate the concept. In production, I'd move to per-token with per-IP fallback."

---

### 6. No Rate Limit on /login Endpoint ⚠️
**Location:** `main.py` /login route (no rate limiting)

**Interview Answer:**
"The /login endpoint has no rate limiting, which is a **brute force vulnerability.** An attacker can:
1. Guess passwords repeatedly without being stopped
2. Enumerate usernames by checking response times

**Production fix:**

1. **Rate limit /login separately:** Allow only 5 failed login attempts per IP per 15 minutes
2. **Account lockout:** After 10 failed attempts, lock the account for 30 minutes
3. **Slow down on failure:** Add delay (`time.sleep(0.5)`) or use exponential backoff after each failure
4. **Monitor:** Log and alert on repeated login failures

**Example:**
```python
@app.post(\"/login\")
def login(username: str, password: str, request: Request):
    # Check if IP is rate limited
    if not rate_limit_login(request.client.host):  # Max 5 attempts per 15 min
        raise HTTPException(status_code=429, detail=\"Too many login attempts\")
    
    user = USERS.get(username)
    if not user or user[\"password\"] != password:
        log_failed_login(username, request.client.host)
        time.sleep(0.5)  # Slow down brute force
        raise HTTPException(status_code=401, detail=\"Invalid credentials\")
    return create_token(...)
```

**In this demo:** I skipped it for simplicity. In production, this would be mandatory."

---

### 7. Error Messages Leak Information ⚠️
**Location:** `main.py` line 23  
```python
raise HTTPException(status_code=401, detail="Invalid credentials")
```

**Interview Answer:**
"This error message is **too specific.** It tells an attacker whether the username exists or the password is wrong:
- If user enters 'bob' + wrong password → 'Invalid credentials' → 'bob' exists
- If user enters 'nonexistent' + any password → same 'Invalid credentials' → Can't tell if user exists

Attackers can use this to **enumerate usernames** (find valid accounts).

**Production fix:**
```python
# Bad (reveals info)
if username not in USERS:
    raise HTTPException(status_code=401, detail=\"Username not found\")
if user[\"password\"] != password:
    raise HTTPException(status_code=401, detail=\"Wrong password\")

# Good (generic)
raise HTTPException(status_code=401, detail=\"Login failed\")
```

**Why:** Even small differences in response time or messages can leak information. The attacker shouldn't know what went wrong—just that they failed.

**In this demo:** I used a generic message, which is actually correct. Good security habit!"

---

### 8. No HTTPS/SSL Enforcement ⚠️
**Location:** Entire app (no HTTPS)

**Interview Answer:**
"This API runs over HTTP only, which means:
1. **Passwords transmitted in plaintext:** Anyone on the network can see login credentials
2. **Tokens visible:** JWT tokens are sent in plain text headers
3. **Man-in-the-Middle (MITM):** Attackers can intercept and modify requests

**Production fix:**

1. **Deploy behind HTTPS:** Use SSL/TLS certificates (Let's Encrypt is free)
2. **Enforce HTTPS:** Redirect all HTTP to HTTPS
3. **Add HSTS header:** Tell browsers to always use HTTPS
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   from starlette.middleware.base import BaseHTTPMiddleware
   
   @app.middleware(\"http\")
   async def add_security_headers(request, call_next):
       response = await call_next(request)
       response.headers[\"Strict-Transport-Security\"] = \"max-age=31536000; includeSubDomains\"
       return response
   ```

**In this demo:** HTTP is fine because it's localhost. In production, HTTPS is **mandatory** for any API handling authentication."

---

### 9. Missing CORS Configuration ⚠️
**Location:** `main.py` (no CORS middleware)

**Interview Answer:**
"Right now, this API can be called from any website (cross-origin requests are unrestricted). This is:

1. **Fine if:** The API is only called by your own frontend (same domain or internal only)
2. **Dangerous if:** You want to prevent arbitrary websites from using your API

**CORS (Cross-Origin Resource Sharing)** is a browser security feature that controls which websites can make requests to your API.

**Production approach:**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[\"https://yourdomain.com\"],  # Only this domain
    allow_methods=[\"POST\", \"GET\"],  # Only these methods
    allow_headers=[\"Authorization\", \"Content-Type\"],
    allow_credentials=True,
)
```

**In this demo:** I didn't add CORS because:
1. It's a backend API, not a public service
2. Adding it requires knowing the frontend URL
3. For internal APIs, CORS isn't always necessary

**Interview answer:** 'CORS is a defensive measure. For internal or backend APIs, it's less critical. For public APIs or SPAs, I'd configure CORS to whitelist only trusted origins.'"

---

### 10. No Input Validation Beyond Type Hints ⚠️
**Location:** `main.py` line 28  
```python
payload: dict = Body(...)
```
Issue: `payload.get("text", "")` accepts any dict; no max length check

**Interview Answer:**
"Right now, I can send a 1GB text field and the app will try to redact it, consuming memory and CPU. This is a **resource exhaustion** vulnerability (Denial of Service).

**Production fix: Use Pydantic models with validation**

```python
from pydantic import BaseModel, Field

class ResourceRequest(BaseModel):
    text: str = Field(..., max_length=10000)  # Max 10KB

@app.post(\"/protected-resource\")
def protected_resource(
    payload: ResourceRequest,
    user: dict = Depends(require_role(\"user\")),
):
    # payload.text is now guaranteed to be ≤10KB
    clean_text = redact(payload.text)
    ...
```

**Why:** Attackers can exploit unbounded inputs to crash the service or consume resources. Pydantic validates automatically and rejects invalid requests with 422.

**In this demo:** I kept it simple with a dict. In production, always use Pydantic models with `max_length`, `regex`, and type validation."

---

### 11. Docker Image Not Running as Non-Root ⚠️
**Location:** `Dockerfile`

**Interview Answer:**
"The Docker container runs as root (UID 0). If someone breaks into the container, they have full system access. Production best practice is to run as a non-root user.

**Fix (not implemented, but good to know):**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m app
USER app

COPY . .
CMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]
```

**Why:** Even if the app is compromised, the attacker is limited to what the 'app' user can do, not root permissions.

**In this demo:** I skipped it because it's a local development setup. For production Docker deployments, running as non-root is standard practice.

**Interview answer:** 'This is a security best practice I'm aware of. For this demo, it's not critical, but I'd implement it in production to limit blast radius if the container is compromised.'"

---

### 12. Plaintext Redis Connection ⚠️
**Location:** `rate_limiter.py` lines 7-8
```python
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
```

**Interview Answer:**
"The connection to Redis has no encryption or authentication. This is:

1. **Fine for:** Local development and internal docker-compose networks (isolated)
2. **Dangerous for:** Production, especially if Redis is exposed on the internet

**Production fixes:**

```python
import os
from redis import Redis
from redis.connection import SSLConnection

redis_client = Redis(
    host=os.getenv(\"REDIS_HOST\"),
    port=int(os.getenv(\"REDIS_PORT\", 6380)),  # SSL port
    password=os.getenv(\"REDIS_PASSWORD\"),     # Auth
    ssl=True,
    ssl_certfile=os.getenv(\"REDIS_CERT_PATH\"),
    decode_responses=True,
)
```

**Why:**
- Without auth: Anyone on the network can read/write rate limit data
- Without TLS: Network traffic is visible in plaintext
- No encryption: MITM attackers can intercept tokens, rate limit info, etc.

**In this demo:** Redis runs in a private docker network, so plaintext is acceptable. In production (AWS ElastiCache, managed Redis), authentication and TLS are **mandatory**."

---

### 13. Error Message Information Leakage (Already Noted) ✓
Already covered in #7.

---

## Summary for Interview

**What I Fixed:**
- ✓ Hardcoded JWT SECRET_KEY → moved to `.env` with python-dotenv

**What I Identified But Didn't Fix (and why):**
1. **Hardcoded demo credentials** — Acceptable for demo, noted bcrypt/OAuth2 for production
2. **Plaintext passwords** — Acceptable for demo, noted hashing approach
3. **HS256 JWT algorithm** — Fine for monolithic app, could use RS256 for microservices
4. **Print logging** — Works for demo, would use logging module in production
5. **Per-username rate limits** — Works for demo, would need per-token/per-IP in production
6. **No /login rate limiting** — Acceptable for demo, would add brute-force protection in production
7. **Generic error messages** — Actually correct! (covered in #7)
8. **HTTP only** — Fine for localhost, mandatory HTTPS in production
9. **No CORS** — Only critical for public APIs; acceptable for internal backend
10. **No input validation** — Works for demo, would use Pydantic `Field(max_length=...)` in production
11. **Root user in Docker** — Good practice to add, but skipped for demo simplicity
12. **Plaintext Redis** — Acceptable for isolated docker network, needs TLS/auth in production

**Key Interview Talking Points:**
- "This is a demo project, so I focused on demonstrating core security concepts (JWT, rate limiting, PII redaction) with simple, understandable code."
- "I identified production security gaps, but didn't over-engineer it for an interview project."
- "Each issue has a clear production solution that I can explain."
- "The one critical fix I did make was moving SECRET_KEY to environment variables, which is fundamental security practice."
