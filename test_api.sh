#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

echo -e "${YELLOW}=== API Security Gateway Local Tests ===${NC}\n"

# Test 1: Health check
echo -e "${YELLOW}Test 1: Health Check${NC}"
curl -s "$BASE_URL/health" | jq .
echo ""

# Test 2: Login with valid credentials (bob - user role)
echo -e "${YELLOW}Test 2: Login with valid credentials (bob - user role)${NC}"
BOB_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "userpass"}')
echo "$BOB_RESPONSE" | jq .
BOB_TOKEN=$(echo "$BOB_RESPONSE" | jq -r '.access_token')
echo "Bob's token: $BOB_TOKEN"
echo ""

# Test 3: Login with valid credentials (alice - admin role)
echo -e "${YELLOW}Test 3: Login with valid credentials (alice - admin role)${NC}"
ALICE_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "adminpass"}')
echo "$ALICE_RESPONSE" | jq .
ALICE_TOKEN=$(echo "$ALICE_RESPONSE" | jq -r '.access_token')
echo "Alice's token: $ALICE_TOKEN"
echo ""

# Test 4: Login with invalid credentials
echo -e "${YELLOW}Test 4: Login with invalid credentials${NC}"
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "wrongpass"}' | jq .
echo ""

# Test 5: Access protected resource with valid token (bob)
echo -e "${YELLOW}Test 5: Access protected resource with valid token (bob)${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "My email is john@example.com and phone is 5551234567"}' | jq .
echo ""

# Test 6: PII Redaction - credit card
echo -e "${YELLOW}Test 6: PII Redaction - credit card${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Payment with card 4111-1111-1111-1111"}' | jq .
echo ""

# Test 7: PII Redaction - multiple types
echo -e "${YELLOW}Test 7: PII Redaction - multiple types${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact alice@company.com, phone 9876543210, card 1234-5678-9012-3456"}' | jq .
echo ""

# Test 8: Missing Authorization header
echo -e "${YELLOW}Test 8: Missing Authorization header${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Content-Type: application/json" \
  -d '{"text": "This should fail"}' | jq .
echo ""

# Test 9: Invalid token
echo -e "${YELLOW}Test 9: Invalid token${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer invalid.token.here" \
  -H "Content-Type: application/json" \
  -d '{"text": "This should fail"}' | jq .
echo ""

# Test 10: Wrong authorization scheme
echo -e "${YELLOW}Test 10: Wrong authorization scheme${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Basic dGVzdDp0ZXN0" \
  -H "Content-Type: application/json" \
  -d '{"text": "This should fail"}' | jq .
echo ""

# Test 11: Rate limiting - send 6 requests (limit is 5)
echo -e "${YELLOW}Test 11: Rate limiting - send 6 requests (limit is 5)${NC}"
for i in {1..6}; do
  echo "Request $i:"
  curl -s -X POST "$BASE_URL/protected-resource" \
    -H "Authorization: Bearer $BOB_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Test rate limit"}' | jq '.error // .message'
  sleep 0.1
done
echo ""

# Test 12: Rate limit recovery (wait ~2 seconds for token refill)
echo -e "${YELLOW}Test 12: Rate limit recovery - wait for token refill${NC}"
echo "Waiting 3 seconds for token bucket to refill..."
sleep 3
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Should work after rate limit recovery"}' | jq .
echo ""

# Test 13: Empty text in payload
echo -e "${YELLOW}Test 13: Empty text in payload${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": ""}' | jq .
echo ""

# Test 14: Alice (admin) can access user-level endpoint
echo -e "${YELLOW}Test 14: Alice (admin) can access user-level endpoint${NC}"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Admin accessing user resource"}' | jq .
echo ""

echo -e "${GREEN}=== All tests completed ===${NC}"
