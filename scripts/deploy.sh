#!/bin/bash
# Deployment Script
# Run this on your LOCAL machine to deploy to DigitalOcean

set -e

# Configuration
DROPLET_IP="${DROPLET_IP:-}"
REPO_URL="${REPO_URL:-}"
PROJECT_DIR="/root/dubbing-mvp"

if [ -z "$DROPLET_IP" ]; then
    echo "Error: DROPLET_IP environment variable not set"
    echo "Usage: DROPLET_IP=your-ip ./scripts/deploy.sh"
    exit 1
fi

echo "=========================================="
echo "Deploying to DigitalOcean Droplet"
echo "=========================================="
echo "Droplet IP: $DROPLET_IP"
echo "Project directory: $PROJECT_DIR"
echo ""

# Deploy via SSH
ssh root@$DROPLET_IP << EOF
set -e

echo "Updating repository..."
cd $PROJECT_DIR

if [ -d ".git" ]; then
    git pull origin main || git pull origin master
else
    echo "Not a git repository. Skipping git pull."
fi

echo "Updating Python dependencies..."
cd python
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
else
    echo "Virtual environment not found. Please run setup_droplet.sh first."
fi

echo "Updating Node.js dependencies..."
cd ../node
if [ -f "package.json" ]; then
    npm install
else
    echo "package.json not found."
fi

echo "Restarting API service..."
if systemctl is-active --quiet dubbing-api; then
    systemctl restart dubbing-api
    echo "API service restarted"
else
    echo "API service not running. Start manually with: cd python && source venv/bin/activate && python app.py"
fi

echo ""
echo "Deployment complete!"
EOF

echo ""
echo "✓ Deployment completed successfully!"
echo ""
echo "To process a video, run:"
echo "  ssh root@$DROPLET_IP 'cd $PROJECT_DIR/node && node src/index.js -i <video>'"
