#!/usr/bin/env python3
"""
Comprehensive test suite for API Security Gateway.
Run with: python3 test_api_suite.py
"""

import requests
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add(self, name: str, passed: bool, message: str = ""):
        status = "✓ PASS" if passed else "✗ FAIL"
        self.tests.append((name, passed, message))
        print(f"{status}: {name}")
        if message:
            print(f"  {message}")
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def summary(self):
        print(f"\n{'='*60}")
        print(f"Total: {self.passed + self.failed} | Passed: {self.passed} | Failed: {self.failed}")
        return self.failed == 0

results = TestResults()

# Fixtures
def get_tokens() -> Dict[str, str]:
    """Login and return tokens for bob and alice."""
    bob_resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": "bob", "password": "userpass"}
    )
    alice_resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": "alice", "password": "adminpass"}
    )
    return {
        "bob": bob_resp.json()["access_token"],
        "alice": alice_resp.json()["access_token"]
    }

print("="*60)
print("API Security Gateway - Test Suite")
print("="*60)
print()

# === Authentication Tests ===
print("AUTH TESTS")
print("-" * 60)

# Test: Valid login
try:
    resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": "bob", "password": "userpass"}
    )
    results.add(
        "Valid login returns 200 and token",
        resp.status_code == 200 and "access_token" in resp.json(),
        f"Status: {resp.status_code}"
    )
except Exception as e:
    results.add("Valid login returns 200 and token", False, str(e))

# Test: Invalid password
try:
    resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": "bob", "password": "wrongpass"}
    )
    results.add(
        "Invalid password returns 401",
        resp.status_code == 401,
        f"Status: {resp.status_code}, Detail: {resp.json().get('detail', 'N/A')}"
    )
except Exception as e:
    results.add("Invalid password returns 401", False, str(e))

# Test: Invalid username
try:
    resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": "nonexistent", "password": "pass"}
    )
    results.add(
        "Invalid username returns 401",
        resp.status_code == 401,
        f"Status: {resp.status_code}"
    )
except Exception as e:
    results.add("Invalid username returns 401", False, str(e))

print()

# === Authorization Tests ===
print("AUTHORIZATION TESTS")
print("-" * 60)

tokens = get_tokens()

# Test: Missing Authorization header
try:
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        json={"text": "test"}
    )
    results.add(
        "Missing Authorization header returns 422",
        resp.status_code == 422,
        f"Status: {resp.status_code}"
    )
except Exception as e:
    results.add("Missing Authorization header returns 422", False, str(e))

# Test: Invalid token
try:
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        headers={"Authorization": "Bearer invalid.token.here"},
        json={"text": "test"}
    )
    results.add(
        "Invalid token returns 401",
        resp.status_code == 401,
        f"Status: {resp.status_code}, Detail: {resp.json().get('detail', 'N/A')}"
    )
except Exception as e:
    results.add("Invalid token returns 401", False, str(e))

# Test: Wrong Bearer scheme
try:
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        json={"text": "test"}
    )
    results.add(
        "Wrong authorization scheme returns 401",
        resp.status_code == 401,
        f"Status: {resp.status_code}"
    )
except Exception as e:
    results.add("Wrong authorization scheme returns 401", False, str(e))

# Test: Valid token grants access
try:
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        headers={"Authorization": f"Bearer {tokens['bob']}"},
        json={"text": "test"}
    )
    results.add(
        "Valid token returns 200",
        resp.status_code == 200,
        f"Status: {resp.status_code}"
    )
except Exception as e:
    results.add("Valid token returns 200", False, str(e))

# Test: Admin role can access user endpoint
try:
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        headers={"Authorization": f"Bearer {tokens['alice']}"},
        json={"text": "test"}
    )
    results.add(
        "Admin role can access user endpoint",
        resp.status_code == 200 and resp.json()["message"].startswith("Hello alice"),
        f"Status: {resp.status_code}, Message: {resp.json().get('message', 'N/A')}"
    )
except Exception as e:
    results.add("Admin role can access user endpoint", False, str(e))

print()

# === PII Redaction Tests ===
print("PII REDACTION TESTS")
print("-" * 60)

test_cases = [
    {
        "name": "Email redaction",
        "input": "Contact john@example.com",
        "should_contain": "[REDACTED_EMAIL]"
    },
    {
        "name": "Phone redaction",
        "input": "Call me at 5551234567",
        "should_contain": "[REDACTED_PHONE]"
    },
    {
        "name": "Credit card redaction",
        "input": "Card 4111-1111-1111-1111 is valid",
        "should_contain": "[REDACTED_CARD]"
    },
    {
        "name": "Multiple PII redaction",
        "input": "Email alice@test.com, phone 9876543210, card 1234-5678-9012-3456",
        "should_contain": "[REDACTED_EMAIL]"
    },
    {
        "name": "Empty text redaction",
        "input": "",
        "should_contain": ""
    }
]

for test in test_cases:
    try:
        resp = requests.post(
            f"{BASE_URL}/protected-resource",
            headers={"Authorization": f"Bearer {tokens['bob']}"},
            json={"text": test["input"]}
        )
        sanitized = resp.json()["sanitized_input"]
        passed = test["should_contain"] in sanitized or (test["should_contain"] == "" and sanitized == "")
        results.add(
            test["name"],
            passed,
            f"Input: '{test['input']}' -> '{sanitized}'"
        )
    except Exception as e:
        results.add(test["name"], False, str(e))

print()

# === Rate Limiting Tests ===
print("RATE LIMITING TESTS")
print("-" * 60)

# Reset tokens for fresh rate limit
tokens = get_tokens()

# Test: Exceed rate limit
try:
    allowed_count = 0
    limited_count = 0
    
    # Send 6 requests with short delays (limit is 5 tokens)
    for i in range(6):
        resp = requests.post(
            f"{BASE_URL}/protected-resource",
            headers={"Authorization": f"Bearer {tokens['bob']}"},
            json={"text": f"Request {i+1}"}
        )
        if resp.status_code == 200 and "message" in resp.json():
            allowed_count += 1
        elif resp.status_code == 429:
            limited_count += 1
        time.sleep(0.05)
    
    # We should have ~2 allowed (initial 5 tokens with some refill) and some limited
    passed = allowed_count > 0 and limited_count > 0
    results.add(
        "Rate limiting enforces token bucket",
        passed,
        f"Allowed: {allowed_count}, Limited: {limited_count}"
    )
except Exception as e:
    results.add("Rate limiting enforces token bucket", False, str(e))

# Test: Rate limit recovery
try:
    tokens = get_tokens()  # Fresh token bucket
    
    # Exhaust tokens
    for i in range(5):
        requests.post(
            f"{BASE_URL}/protected-resource",
            headers={"Authorization": f"Bearer {tokens['bob']}"},
            json={"text": f"Drain {i+1}"}
        )
    
    # Should be rate limited
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        headers={"Authorization": f"Bearer {tokens['bob']}"},
        json={"text": "Should be blocked"}
    )
    blocked = resp.status_code == 429
    
    # Wait for refill
    time.sleep(2)
    
    # Should work again after refill
    resp = requests.post(
        f"{BASE_URL}/protected-resource",
        headers={"Authorization": f"Bearer {tokens['bob']}"},
        json={"text": "Should work"}
    )
    recovered = resp.status_code == 200
    
    results.add(
        "Rate limit recovers after token refill",
        blocked and recovered,
        f"Was blocked: {blocked}, Recovered: {recovered}"
    )
except Exception as e:
    results.add("Rate limit recovers after token refill", False, str(e))

print()

# === Health Check ===
print("HEALTH CHECK TESTS")
print("-" * 60)

try:
    resp = requests.get(f"{BASE_URL}/health")
    results.add(
        "Health endpoint returns 200 and healthy status",
        resp.status_code == 200 and resp.json()["status"] == "healthy",
        f"Status: {resp.status_code}, Response: {resp.json()}"
    )
except Exception as e:
    results.add("Health endpoint returns 200 and healthy status", False, str(e))

print()

# === Summary ===
if results.summary():
    print("\n✓ All tests passed!")
    sys.exit(0)
else:
    print(f"\n✗ {results.failed} test(s) failed")
    sys.exit(1)
