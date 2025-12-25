#!/bin/bash
# Individual Service Test Script
# Tests each API endpoint individually

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=========================================="
echo "Service Testing"
echo "=========================================="
echo "API URL: $API_URL"
echo ""

# Test health endpoint
echo "[1/5] Testing health endpoint..."
HEALTH=$(curl -s "$API_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed"
    exit 1
fi

# Test transcription (requires audio file)
echo ""
echo "[2/5] Testing transcription endpoint..."
echo "Note: Requires audio file. Skipping for now."
echo "  To test: curl -X POST -F 'file=@audio.wav' $API_URL/transcribe"

# Test translation
echo ""
echo "[3/5] Testing translation endpoint..."
TRANSLATION=$(curl -s -X POST "$API_URL/translate" \
    -H "Content-Type: application/json" \
    -d '{
        "text": "Hello, how are you?",
        "source_lang": "eng_Latn",
        "target_lang": "uzb_Latn"
    }')

if echo "$TRANSLATION" | grep -q "translated_text"; then
    echo "✓ Translation test passed"
    echo "$TRANSLATION" | python3 -m json.tool
else
    echo "✗ Translation test failed"
    echo "$TRANSLATION"
fi

# Test emotion detection
echo ""
echo "[4/5] Testing emotion detection endpoint..."
EMOTION=$(curl -s -X POST "$API_URL/emotion" \
    -H "Content-Type: application/json" \
    -d '{
        "text": "I am so happy today!"
    }')

if echo "$EMOTION" | grep -q "emotion"; then
    echo "✓ Emotion detection test passed"
    echo "$EMOTION" | python3 -m json.tool
else
    echo "✗ Emotion detection test failed"
    echo "$EMOTION"
fi

# Test stats endpoint
echo ""
echo "[5/5] Testing stats endpoint..."
STATS=$(curl -s "$API_URL/stats")
if echo "$STATS" | grep -q "device"; then
    echo "✓ Stats endpoint test passed"
    echo "$STATS" | python3 -m json.tool
else
    echo "✗ Stats endpoint test failed"
    echo "$STATS"
fi

echo ""
echo "=========================================="
echo "Service Tests Completed"
echo "=========================================="

