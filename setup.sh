#!/bin/bash

# Glass Box PII Guardrail - Setup Script
# Installs all dependencies for both backend and frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Glass Box PII Guardrail - Setup                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Find compatible Python version (3.9-3.12, spaCy doesn't support 3.13+)
PYTHON_CMD=""
for ver in python3.12 python3.11 python3.10 python3.9; do
    if command -v $ver &> /dev/null; then
        PYTHON_CMD=$ver
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    # Check if default python3 is compatible
    if command -v python3 &> /dev/null; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
        PY_MINOR=$(echo $PY_VER | cut -d. -f2)

        if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 9 ] && [ "$PY_MINOR" -le 12 ]; then
            PYTHON_CMD="python3"
        fi
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: No compatible Python version found (3.9-3.12 required)${NC}"
    echo -e "${RED}spaCy and Presidio don't support Python 3.13+ yet${NC}"
    echo -e "${YELLOW}Install Python 3.12: brew install python@3.12${NC}"
    exit 1
fi

echo -e "${GREEN}Using $PYTHON_CMD ($($PYTHON_CMD --version))${NC}"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

echo -e "${YELLOW}Setting up Backend...${NC}"
cd "$BACKEND_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "  Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo -e "  Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Download spaCy model
echo -e "  Downloading spaCy language model..."
python -m spacy download en_core_web_sm -q 2>/dev/null || python -m spacy download en_core_web_sm

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "  Creating .env file..."
    cp "$SCRIPT_DIR/.env.example" .env
    echo -e "${YELLOW}  Note: Edit backend/.env to add your OPENROUTER_API_KEY${NC}"
    echo -e "${YELLOW}        (Demo mode works without API key)${NC}"
fi

echo -e "${GREEN}  Backend setup complete!${NC}"
echo ""

echo -e "${YELLOW}Setting up Frontend...${NC}"
cd "$FRONTEND_DIR"

# Detect package manager
if command -v pnpm &> /dev/null; then
    PKG_MGR="pnpm"
elif command -v yarn &> /dev/null; then
    PKG_MGR="yarn"
else
    PKG_MGR="npm"
fi

echo -e "  Using $PKG_MGR as package manager..."

# Install Node dependencies
echo -e "  Installing Node.js dependencies..."
$PKG_MGR install

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo -e "  Creating .env.local file..."
    cp .env.local.example .env.local
fi

echo -e "${GREEN}  Frontend setup complete!${NC}"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                                           ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  To start the servers, run:                                ║${NC}"
echo -e "${GREEN}║    ${BLUE}./start.sh${GREEN}                                             ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  Or start them individually:                               ║${NC}"
echo -e "${GREEN}║    Backend:  ${BLUE}cd backend && source venv/bin/activate${GREEN}       ║${NC}"
echo -e "${GREEN}║              ${BLUE}uvicorn main:app --reload --port 8000${GREEN}        ║${NC}"
echo -e "${GREEN}║    Frontend: ${BLUE}cd frontend && npm run dev${GREEN}                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
