#!/bin/bash

# Quick Reference Guide for Testing API Security Gateway Locally

echo "================================================================"
echo "API Security Gateway - Local Testing Quick Reference"
echo "================================================================"
echo ""

# === Manual Testing with curl ===
cat << 'EOF'
1. START THE APP
   cd ./api-security-gateway
   docker compose up -d

2. QUICK MANUAL TESTS (copy-paste these commands)

   a) Health Check:
      curl http://localhost:8000/health | jq .

   b) Login (bob - user role):
      curl -X POST http://localhost:8000/login \
        -H "Content-Type: application/json" \
        -d '{"username": "bob", "password": "userpass"}' | jq .

   c) Login (alice - admin role):
      curl -X POST http://localhost:8000/login \
        -H "Content-Type: application/json" \
        -d '{"username": "alice", "password": "adminpass"}' | jq .

   d) Access Protected Resource (save token to variable first):
      TOKEN="<your-token-here>"
      curl -X POST http://localhost:8000/protected-resource \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"text": "My email is john@example.com"}' | jq .

3. RUN FULL TEST SUITE (bash)
   cd ./api-security-gateway
   ./test_api.sh

4. VIEW LOGS
   docker compose logs -f api
   docker compose logs -f redis

5. STOP THE APP
   docker compose down

================================================================
COMMON TEST SCENARIOS
================================================================

Test: PII Redaction (Email)
  TOKEN=$(curl -s -X POST http://localhost:8000/login \
    -H "Content-Type: application/json" \
    -d '{"username": "bob", "password": "userpass"}' | jq -r '.access_token')
  
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Contact me at john@example.com"}' | jq '.sanitized_input'

Test: PII Redaction (Phone)
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Call 5551234567"}' | jq '.sanitized_input'

Test: PII Redaction (Credit Card)
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Card: 4111-1111-1111-1111"}' | jq '.sanitized_input'

Test: Rate Limiting (send 6 requests, limit is 5)
  for i in {1..6}; do
    curl -s -X POST http://localhost:8000/protected-resource \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"text": "Test"}' | jq '.error // .message'
  done

Test: Rate Limit Recovery (wait 2 seconds for token refill)
  sleep 2
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Should work now"}' | jq '.message'

Test: Invalid Credentials
  curl -s -X POST http://localhost:8000/login \
    -H "Content-Type: application/json" \
    -d '{"username": "bob", "password": "wrongpass"}' | jq '.detail'

Test: Missing Authorization Header
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Content-Type: application/json" \
    -d '{"text": "test"}' | jq '.detail'

Test: Invalid Token
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Authorization: Bearer invalid.token.here" \
    -H "Content-Type: application/json" \
    -d '{"text": "test"}' | jq '.detail'

Test: Admin Role Access
  ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/login \
    -H "Content-Type: application/json" \
    -d '{"username": "alice", "password": "adminpass"}' | jq -r '.access_token')
  
  curl -s -X POST http://localhost:8000/protected-resource \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Admin user test"}' | jq '.message'

================================================================
INTERACTIVE TESTING (save this as test_interactive.sh)
================================================================

Save this script and run: bash test_interactive.sh

#!/bin/bash
BASE_URL="http://localhost:8000"

# Get tokens
BOB_TOKEN=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "userpass"}' | jq -r '.access_token')

ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "adminpass"}' | jq -r '.access_token')

echo "Bob's token: $BOB_TOKEN"
echo "Admin's token: $ADMIN_TOKEN"
echo ""
echo "Now you can use these tokens in curl commands"

================================================================
DOCKER COMPOSE REFERENCE
================================================================

Start: docker compose up -d
Stop:  docker compose down
Logs:  docker compose logs -f
Restart: docker compose restart
Remove: docker compose down -v

View running containers: docker compose ps
Execute command: docker compose exec api /bin/bash

================================================================
EOF
