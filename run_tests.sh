#!/bin/bash

BASE_URL="http://localhost:8000"

echo "======================================================================"
echo "API Security Gateway - Interactive Testing Tool"
echo "======================================================================"
echo ""

# Get fresh tokens
echo "Authenticating users..."
BOB_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "userpass"}')
BOB_TOKEN=$(echo "$BOB_RESPONSE" | jq -r '.access_token')

ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "adminpass"}')
ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | jq -r '.access_token')

echo "✓ Tokens obtained"
echo ""
echo "Available tokens for testing:"
echo "  BOB_TOKEN=$BOB_TOKEN"
echo "  ADMIN_TOKEN=$ADMIN_TOKEN"
echo ""
echo "======================================================================"
echo "QUICK TESTS"
echo "======================================================================"
echo ""

# Test 1: Health
echo "1. Health Check:"
curl -s "$BASE_URL/health" | jq .
echo ""

# Test 2: Bob accessing protected resource
echo "2. Bob accessing protected resource:"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "My email is john@example.com and call 5551234567"}' | jq .
echo ""

# Test 3: Admin accessing protected resource
echo "3. Admin accessing protected resource:"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Card 4111-1111-1111-1111 is my payment method"}' | jq .
echo ""

# Test 4: Invalid token
echo "4. Invalid token (should get 401):"
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer invalid.token" \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' | jq .
echo ""

# Test 5: Rate limiting
echo "5. Rate limiting test (5 token limit, sending 6 requests):"
for i in {1..6}; do
  echo -n "  Request $i: "
  curl -s -X POST "$BASE_URL/protected-resource" \
    -H "Authorization: Bearer $BOB_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "Test"}' | jq -r '.error // .message' | head -c 40
  echo ""
  sleep 0.1
done
echo ""

# Test 6: Rate limit recovery
echo "6. Rate limit recovery (waiting 3 seconds for token refill):"
sleep 3
curl -s -X POST "$BASE_URL/protected-resource" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Should work after refill"}' | jq .
echo ""

echo "======================================================================"
echo "NEXT STEPS"
echo "======================================================================"
echo ""
echo "You can also test manually with curl. Here are some examples:"
echo ""
echo "# Get a fresh token"
echo "TOKEN=\$(curl -s -X POST $BASE_URL/login \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"username\": \"bob\", \"password\": \"userpass\"}' | jq -r '.access_token')"
echo ""
echo "# Use it in requests"
echo "curl -X POST $BASE_URL/protected-resource \\"
echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"Your text here\"}'"
echo ""
echo "Run './test_api.sh' for a complete test suite"
echo ""
