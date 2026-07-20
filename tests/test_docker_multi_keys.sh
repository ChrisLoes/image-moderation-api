#!/bin/bash
# Test multiple API keys in Docker container

set -e

API_URL="http://localhost:8000"
TEST_IMAGE_PATH="${1:-.}"

# Minimal test PNG (1x1 pixel)
MINIMAL_PNG_BASE64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

echo "============================================"
echo "Testing Multiple API Keys in Docker"
echo "============================================"
echo ""

# Test 1: Dev key should work
echo "[1/5] Testing DEV API key..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: wievoll-dev-2324032lkADSJfk2l3" \
  -F "file=@${TEST_IMAGE_PATH}/test_input.png" \
  "${API_URL}/faces/blur")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ DEV key accepted (HTTP 200)"
    if echo "$BODY" | grep -q "success"; then
        echo "✓ Response valid JSON"
    fi
else
    echo "✗ DEV key failed with HTTP $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi

echo ""

# Test 2: Prod key should work
echo "[2/5] Testing PROD API key..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: wievoll-prod-fsalkjWkdWlmcVje2ß927" \
  -F "file=@${TEST_IMAGE_PATH}/test_input.png" \
  "${API_URL}/faces/blur")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ PROD key accepted (HTTP 200)"
    if echo "$BODY" | grep -q "success"; then
        echo "✓ Response valid JSON"
    fi
else
    echo "✗ PROD key failed with HTTP $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi

echo ""

# Test 3: Invalid key should fail
echo "[3/5] Testing INVALID API key (should fail)..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: invalid-key-12345" \
  -F "file=@${TEST_IMAGE_PATH}/test_input.png" \
  "${API_URL}/faces/blur")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "401" ]; then
    echo "✓ Invalid key rejected (HTTP 401)"
    if echo "$BODY" | grep -q "Invalid or missing API key"; then
        echo "✓ Correct error message"
    fi
else
    echo "✗ Invalid key should have been rejected, got HTTP $HTTP_CODE"
    exit 1
fi

echo ""

# Test 4: Dev key on NSFW endpoint
echo "[4/5] Testing DEV key on NSFW endpoint..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: wievoll-dev-2324032lkADSJfk2l3" \
  -F "file=@${TEST_IMAGE_PATH}/test_input.png" \
  "${API_URL}/nsfw/detect")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ DEV key works on NSFW endpoint (HTTP 200)"
else
    echo "✗ DEV key failed on NSFW endpoint with HTTP $HTTP_CODE"
    exit 1
fi

echo ""

# Test 5: Prod key on NSFW endpoint
echo "[5/5] Testing PROD key on NSFW endpoint..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: wievoll-prod-fsalkjWkdWlmcVje2ß927" \
  -F "file=@${TEST_IMAGE_PATH}/test_input.png" \
  "${API_URL}/nsfw/detect")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ PROD key works on NSFW endpoint (HTTP 200)"
else
    echo "✗ PROD key failed on NSFW endpoint with HTTP $HTTP_CODE"
    exit 1
fi

echo ""
echo "============================================"
echo "All tests passed! ✓"
echo "============================================"
echo ""
echo "Summary:"
echo "  ✓ Both DEV and PROD keys accepted"
echo "  ✓ Invalid key correctly rejected"
echo "  ✓ Both keys work on all endpoints"
