# API Security Gateway

A FastAPI application that demonstrates core API security patterns. This project implements JWT authentication, role-based access control, Redis-backed rate limiting, and PII redaction in a single middleware pipeline.

## How It Works

The application processes requests through these security layers in order:

1. JWT Authentication - Verifies the token signature and expiry time. Returns 401 if invalid or missing.
2. Role-Based Access Control - Checks if the user's role is permitted. Returns 403 if insufficient permissions.
3. Rate Limiting - Enforces token bucket limits per user via Redis. Returns 429 if limit exceeded.
4. PII Redaction - Scans request text for sensitive data and redacts emails, phone numbers, and credit cards.
5. Protected Route - Executes the application logic with a clean, sanitized request.

## Technology Stack

Component: API Framework
Technology: FastAPI
Reason: Fast, async-ready, built-in dependency injection for middleware

Component: Authentication
Technology: PyJWT
Reason: Lightweight JWT encoding and decoding

Component: Authorization
Technology: Python dictionary
Reason: Simple role-based access control without external dependencies

Component: Rate Limiting
Technology: Redis with redis-py library
Reason: Distributed state tracking works correctly across multiple API replicas

Component: PII Detection
Technology: Python regex (regular expressions)
Reason: Transparent and fully understandable, no black-box dependencies

Component: Deployment
Technology: Docker Compose
Reason: Reproducible, contains both API and Redis in single stack

## Getting Started

Install Docker and Docker Compose. Then run:

cd api-security-gateway
docker-compose up --build

The API will be available at http://localhost:8000

## Example Usage

### Step 1: Login

Send credentials to get a JWT token:

curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "adminpass"}'

Response:

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

### Step 2: Use the Protected Resource

Send the token in the Authorization header:

curl -X POST http://localhost:8000/protected-resource \
  -H "Authorization: Bearer <your-token-here>" \
  -H "Content-Type: application/json" \
  -d '{"text": "My email is john@example.com and phone is 5551234567"}'

Response shows redacted PII:

{
  "message": "Hello alice, request processed.",
  "sanitized_input": "My email is [REDACTED_EMAIL] and phone is [REDACTED_PHONE]"
}

### Step 3: Test Rate Limiting

Make the same request 6 times quickly. After 5 requests, you will get:

{
  "error": "Rate limit exceeded. Try again later."
}

Wait a few seconds for tokens to refill, then try again.

### Step 4: Test Authentication Failures

Send a request without the Authorization header:

curl -X POST http://localhost:8000/protected-resource \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

Response (401 error):

{
  "detail": "Field required"
}

## API Endpoints

POST /login
Authorization: Not required
Description: Submit username and password to receive a JWT token

POST /protected-resource
Authorization: Bearer token required
Description: Submit text for processing. Text is redacted for PII before processing.

GET /health
Authorization: Not required
Description: Health check endpoint. Returns status if API is running.

## Project Files

main.py
Defines the FastAPI application and all routes. Orchestrates the request flow through authentication, authorization, rate limiting, and PII redaction.

auth.py
Handles JWT token creation and verification. Implements role-based access control. Loads the SECRET_KEY from environment variables.

rate_limiter.py
Implements token bucket rate limiting using Redis. Each user gets a bucket that refills over time. Uses Lua scripts for atomic operations.

pii.py
Scans text for sensitive patterns using regular expressions. Redacts emails, phone numbers, and credit card numbers.

requirements.txt
Lists Python dependencies: fastapi, uvicorn, pyjwt, redis, python-dotenv

Dockerfile
Defines the Docker image for the API service. Uses Python 3.12 slim base image.

docker-compose.yml
Orchestrates the API and Redis services. Configures networking and environment variables.

.env
Local development environment file. Contains SECRET_KEY for local testing. Never commit this to git.

.gitignore
Prevents sensitive files like .env from being committed to version control.

## Key Design Choices

Authentication as a Dependency

The authentication check is implemented as a FastAPI dependency. This means it runs before the route function executes. If authentication fails, the response is returned immediately without running the rest of the code. This is the fail-fast pattern.

Rate Limiting Inside the Route

Rate limiting runs after authentication because it needs the user ID from the decoded token. The order matters: you must authenticate before you can rate limit.

Token Bucket Algorithm

This project uses the token bucket algorithm instead of a fixed-window counter. Token bucket allows small bursts of requests while still enforcing overall rate limits. It is more user-friendly than fixed counters.

Redis for Distributed State

Rate limit state is stored in Redis instead of application memory. This is important when you have multiple API instances behind a load balancer. Without Redis, each instance would have its own separate bucket and limits would not work correctly.

Regex for PII Detection

The PII detection uses simple regular expressions. This approach is transparent and easy to understand. In production, you would add NLP-based Named Entity Recognition for better accuracy, but regex is sufficient for this demonstration.

## Security Considerations

This is a demonstration project for learning and interview purposes. See SECURITY_REVIEW.md for a complete analysis of security issues, production recommendations, and interview talking points.

Key points:

The SECRET_KEY is stored in environment variables, not hardcoded in source code.

Demo credentials are intentionally simple. Production systems use password hashing and external identity providers.

HTTPS is not enabled because the app runs on localhost. Production deployments require HTTPS.

See SECURITY_REVIEW.md for detailed security discussion.

## Testing

To run the full test suite:

cd api-security-gateway
./run_tests.sh

This script tests all endpoints, PII redaction, rate limiting, authentication, and authorization.

For manual testing with curl, see TESTING.md for examples and command reference.

## Troubleshooting

API fails to start

Check that Docker is running and no other service is using port 8000.

Run: docker-compose logs api

Rate limiting does not work

Verify Redis is running: docker-compose ps

Check Redis connection: docker-compose logs api

Tokens are rejected as invalid

Verify the SECRET_KEY environment variable is set correctly.

Check that the token was recently created (tokens expire after 1 hour).

## Next Steps

For learning:
- Modify the rate limit window size in rate_limiter.py
- Add new PII patterns to pii.py
- Extend the USERS dictionary to add more demo users

For production readiness:
- Add password hashing using bcrypt
- Replace hardcoded users with a real database
- Add HTTPS/TLS support
- Configure CORS for your frontend
- Add input validation with Pydantic models
- Add structured logging instead of print statements

See SECURITY_REVIEW.md for detailed production recommendations.

## License

This is a demonstration project for educational purposes.
