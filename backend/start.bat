@echo off
REM GutBot Startup Script for Windows

echo ========================================
echo    GutBot - AI Health Chatbot
echo    Startup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo [1] Starting Backend Server...
start cmd /k "python app_enhanced.py"

timeout /t 3 /nobreak

echo.
echo [2] Installing Frontend Dependencies...
cd frontend
call npm install

echo.
echo [3] Starting Frontend Development Server...
call npm run dev

cd ..

echo.
echo ========================================
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo Health Check: http://localhost:5000/health
echo ========================================
