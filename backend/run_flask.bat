@echo off
REM Start Flask App with Diagnostic Output

echo.
echo =============================================================================
echo STARTING FLASK APP WITH LLM CONFIGURATION
echo =============================================================================
echo.
echo Checking prerequisites...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

echo ✅ Python is installed
echo.
echo Checking required packages...
python -c "import flask, flask_cors, PyPDF2, faiss, sentence_transformers, boto3, dotenv" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Some packages might be missing
    echo Run: pip install flask flask-cors PyPDF2 faiss-cpu sentence-transformers boto3 python-dotenv
    echo.
)

echo.
echo =============================================================================
echo Starting Flask App on http://localhost:5000
echo =============================================================================
echo.
echo What to do:
echo 1. Open browser and go to http://localhost:5000
echo 2. Upload a PDF file
echo 3. Type a question and click Send
echo 4. Check this terminal for LLM debug messages:
echo    - [LLM Config] messages show configuration
echo    - [LLM Call] messages show model calls
echo.
echo Press Ctrl+C to stop the server
echo.
echo =============================================================================
echo.

cd /d "%~dp0"
python app.py

pause
