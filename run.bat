@echo off
REM TenChat NeuroBooster Startup Script (Windows)

echo ===================================
echo TenChat NeuroBooster v1.0
echo ===================================
echo.

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo .env created. Please edit it and add your AI_API_KEY
    echo.
    pause
)

REM Check if Docker is running
docker version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running!
    echo Please start Docker Desktop
    pause
    exit /b 1
)

echo Starting TenChat NeuroBooster...
echo.

REM Create directories if they don't exist
if not exist data mkdir data
if not exist logs mkdir logs

REM Start Docker Compose
docker-compose up -d

if errorlevel 1 (
    echo.
    echo Error: Failed to start containers!
    echo Check logs: docker-compose logs
    pause
    exit /b 1
)

echo.
echo TenChat NeuroBooster started successfully!
echo.
echo Access points:
echo    UI:  http://localhost:8501
echo    API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo Useful commands:
echo    View logs:    docker-compose logs -f
echo    Stop service: docker-compose down
echo    Restart:      docker-compose restart
echo.
pause
