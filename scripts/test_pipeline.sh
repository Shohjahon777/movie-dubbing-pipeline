#!/bin/bash
# End-to-end Pipeline Test Script
# Tests the complete dubbing pipeline with a sample video

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_VIDEO="${1:-}"

echo "=========================================="
echo "Dubbing Pipeline - End-to-End Test"
echo "=========================================="

# Check if API is running
echo "Checking API health..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Error: API is not running"
    echo "Please start the API first:"
    echo "  cd python && source venv/bin/activate && python app.py"
    exit 1
fi

API_STATUS=$(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$API_STATUS" != "healthy" ]; then
    echo "Error: API is not healthy"
    exit 1
fi

echo "✓ API is healthy"

# Check if test video is provided
if [ -z "$TEST_VIDEO" ]; then
    echo ""
    echo "No test video provided."
    echo "Usage: $0 <path/to/test_video.mp4>"
    echo ""
    echo "To download a test video, run:"
    echo "  pip install yt-dlp"
    echo "  yt-dlp -o data/input/test.mp4 'https://youtube.com/watch?v=VIDEO_ID'"
    exit 1
fi

if [ ! -f "$TEST_VIDEO" ]; then
    echo "Error: Test video not found: $TEST_VIDEO"
    exit 1
fi

echo "Test video: $TEST_VIDEO"
echo ""

# Run pipeline
cd "$PROJECT_DIR/node"
node src/index.js -i "$TEST_VIDEO" -o "$PROJECT_DIR/data/output/test_dubbed.mp4"

echo ""
echo "=========================================="
echo "Test Completed!"
echo "=========================================="
echo "Output: $PROJECT_DIR/data/output/test_dubbed.mp4"

