#!/bin/bash
# GutBot - Local Development Startup Script
# Starts backend (Flask dev server) and frontend (Vite dev server)

set -e

echo "========================================"
echo "  GutBot - AI Medical Chatbot"
echo "  Local Development Startup"
echo "========================================"

# Python check
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Install Python 3.10+ from https://www.python.org/"
    exit 1
fi

# Node check
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed. Install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "[1/5] Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "[2/5] Activating virtual environment..."
source venv/bin/activate

echo "[3/5] Installing backend dependencies..."
pip install -q -r requirements.txt

# Verify .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found."
    echo "  Run: cp .env.example .env  then fill in your credentials."
    exit 1
fi

echo "[4/5] Starting backend server on port 8000..."
python app.py &
BACKEND_PID=$!

sleep 3

# Frontend (expected in ../frontend relative to this script)
FRONTEND_DIR="$(dirname "$0")/../frontend"
if [ -d "$FRONTEND_DIR" ]; then
    echo "[5/5] Starting frontend dev server..."
    cd "$FRONTEND_DIR"
    npm install -q
    npm run dev &
    FRONTEND_PID=$!
    cd -
else
    echo "[5/5] Frontend directory not found at $FRONTEND_DIR — skipping."
    FRONTEND_PID=""
fi

echo ""
echo "========================================"
echo "  Backend  : http://localhost:8000"
echo "  Frontend : http://localhost:3000"
echo "========================================"
echo "Press Ctrl+C to stop all servers."

if [ -n "$FRONTEND_PID" ]; then
    wait $BACKEND_PID $FRONTEND_PID
else
    wait $BACKEND_PID
fi
