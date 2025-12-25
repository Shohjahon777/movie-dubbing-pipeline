#!/bin/bash
# DigitalOcean GPU Droplet Setup Script
# Automates setup of all dependencies for the dubbing pipeline
# Idempotent - safe to run multiple times

set -e

echo "=========================================="
echo "DigitalOcean GPU Droplet Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Update system packages
echo -e "\n${YELLOW}[1/12] Updating system packages...${NC}"
apt update && apt upgrade -y

# Install basic dependencies
echo -e "\n${YELLOW}[2/12] Installing basic dependencies...${NC}"
apt install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    htop \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Check and install CUDA
echo -e "\n${YELLOW}[3/12] Checking CUDA installation...${NC}"
if command -v nvidia-smi &> /dev/null; then
    CUDA_VERSION=$(nvidia-smi | grep -oP 'CUDA Version: \K[0-9]+\.[0-9]+' || echo "unknown")
    echo -e "${GREEN}CUDA already installed: $CUDA_VERSION${NC}"
else
    echo -e "${YELLOW}CUDA not found. Installing CUDA 12.1...${NC}"
    echo "Note: CUDA installation requires manual steps. Please install CUDA toolkit manually."
    echo "Visit: https://developer.nvidia.com/cuda-downloads"
fi

# Install Python 3.10
echo -e "\n${YELLOW}[4/12] Installing Python 3.10...${NC}"
if command -v python3.10 &> /dev/null; then
    echo -e "${GREEN}Python 3.10 already installed${NC}"
else
    add-apt-repository -y ppa:deadsnakes/ppa
    apt update
    apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
fi

# Install Node.js 20.x
echo -e "\n${YELLOW}[5/12] Installing Node.js 20.x...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Node.js already installed: $NODE_VERSION${NC}"
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
fi

# Install FFmpeg with GPU support
echo -e "\n${YELLOW}[6/12] Installing FFmpeg...${NC}"
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}FFmpeg already installed${NC}"
else
    apt install -y ffmpeg
fi

# Install Docker
echo -e "\n${YELLOW}[7/12] Installing Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker already installed${NC}"
else
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
fi

# Create project directory
echo -e "\n${YELLOW}[8/12] Setting up project directory...${NC}"
PROJECT_DIR="/root/dubbing-mvp"
if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    echo -e "${GREEN}Created project directory: $PROJECT_DIR${NC}"
else
    echo -e "${GREEN}Project directory already exists${NC}"
fi

# Setup Python virtual environment
echo -e "\n${YELLOW}[9/12] Setting up Python virtual environment...${NC}"
if [ ! -d "$PROJECT_DIR/python/venv" ]; then
    cd "$PROJECT_DIR"
    python3.10 -m venv python/venv
    source python/venv/bin/activate
    pip install --upgrade pip
    echo -e "${GREEN}Python virtual environment created${NC}"
else
    echo -e "${GREEN}Python virtual environment already exists${NC}"
fi

# Install Python dependencies
echo -e "\n${YELLOW}[10/12] Installing Python dependencies...${NC}"
if [ -f "$PROJECT_DIR/python/requirements.txt" ]; then
    source "$PROJECT_DIR/python/venv/bin/activate"
    pip install -r "$PROJECT_DIR/python/requirements.txt"
    echo -e "${GREEN}Python dependencies installed${NC}"
else
    echo -e "${YELLOW}requirements.txt not found, skipping...${NC}"
fi

# Install Node.js dependencies
echo -e "\n${YELLOW}[11/12] Installing Node.js dependencies...${NC}"
if [ -f "$PROJECT_DIR/node/package.json" ]; then
    cd "$PROJECT_DIR/node"
    npm install
    echo -e "${GREEN}Node.js dependencies installed${NC}"
else
    echo -e "${YELLOW}package.json not found, skipping...${NC}"
fi

# Configure firewall
echo -e "\n${YELLOW}[12/12] Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp  # SSH
    ufw allow 8000/tcp  # FastAPI
    ufw --force enable
    echo -e "${GREEN}Firewall configured${NC}"
else
    echo -e "${YELLOW}UFW not installed, skipping firewall setup${NC}"
fi

# Summary
echo -e "\n${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"

echo -e "\n${YELLOW}System Information:${NC}"
echo "  OS: $(lsb_release -d | cut -f2)"
echo "  Python: $(python3 --version)"
echo "  Node.js: $(node --version)"
echo "  npm: $(npm --version)"

if command -v nvidia-smi &> /dev/null; then
    echo -e "\n${YELLOW}GPU Information:${NC}"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
else
    echo -e "\n${YELLOW}GPU: Not detected${NC}"
fi

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "  1. Clone your repository to $PROJECT_DIR"
echo "  2. Run: cd $PROJECT_DIR/python && source venv/bin/activate"
echo "  3. Run: python download_models.py --model-dir ./models"
echo "  4. Start API: python app.py"
echo "  5. Process video: cd ../node && node src/index.js -i <video>"

echo -e "\n${GREEN}Setup completed successfully!${NC}"
