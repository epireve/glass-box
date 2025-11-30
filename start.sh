#!/bin/bash

# Glass Box PII Guardrail - Development Server Starter
# Runs both backend (FastAPI) and frontend (Next.js) concurrently

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
echo -e "${BLUE}║         Glass Box PII Guardrail - Dev Server               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if backend venv exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}Python virtual environment not found. Running setup first...${NC}"
    bash "$SCRIPT_DIR/setup.sh"
fi

# Check if frontend node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Node modules not found. Running setup first...${NC}"
    bash "$SCRIPT_DIR/setup.sh"
fi

# Start Backend
echo -e "${GREEN}Starting Backend (FastAPI) on http://localhost:8000${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start Frontend
echo -e "${GREEN}Starting Frontend (Next.js) on http://localhost:3000${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Servers are running!                                      ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  Frontend: ${BLUE}http://localhost:3000${GREEN}                        ║${NC}"
echo -e "${GREEN}║  Backend:  ${BLUE}http://localhost:8000${GREEN}                        ║${NC}"
echo -e "${GREEN}║  API Docs: ${BLUE}http://localhost:8000/docs${GREEN}                   ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  Press Ctrl+C to stop both servers                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
