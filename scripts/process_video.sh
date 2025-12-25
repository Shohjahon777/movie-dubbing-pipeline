#!/bin/bash
# Video Processing Script
# Run this on DigitalOcean droplet to process a video

set -e

PROJECT_DIR="/root/dubbing-mvp"
INPUT_VIDEO="$1"

if [ -z "$INPUT_VIDEO" ]; then
    echo "Usage: $0 <path/to/video.mp4>"
    echo ""
    echo "Example:"
    echo "  $0 /root/dubbing-mvp/data/input/test.mp4"
    exit 1
fi

if [ ! -f "$INPUT_VIDEO" ]; then
    echo "Error: Video file not found: $INPUT_VIDEO"
    exit 1
fi

echo "=========================================="
echo "Dubbing Pipeline - Video Processing"
echo "=========================================="
echo "Input video: $INPUT_VIDEO"
echo ""

# Generate output filename
INPUT_DIR=$(dirname "$INPUT_VIDEO")
INPUT_NAME=$(basename "$INPUT_VIDEO" | sed 's/\.[^.]*$//')
OUTPUT_VIDEO="$INPUT_DIR/${INPUT_NAME}_dubbed.mp4"

echo "Output video: $OUTPUT_VIDEO"
echo ""

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Error: API is not running. Please start it first:"
    echo "  cd $PROJECT_DIR/python && source venv/bin/activate && python app.py"
    exit 1
fi

# Run pipeline
cd "$PROJECT_DIR/node"
node src/index.js -i "$INPUT_VIDEO" -o "$OUTPUT_VIDEO"

echo ""
echo "=========================================="
echo "Processing Complete!"
echo "=========================================="
echo "Output video: $OUTPUT_VIDEO"
echo ""
echo "To download the result:"
echo "  scp root@$(hostname -I | awk '{print $1}'):$OUTPUT_VIDEO ./"
