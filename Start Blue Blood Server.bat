@echo off
cd /d "%~dp0"
set "PYTHON=python"
if exist "%USERPROFILE%\miniconda3\python.exe" set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
"%PYTHON%" -c "import websockets" >nul 2>&1
if errorlevel 1 (
  echo Installing the WebSocket server dependency...
  "%PYTHON%" -m pip install -r requirements-server.txt
  if errorlevel 1 (
    echo.
    echo Could not install the server dependency. Check your internet connection.
    pause
    exit /b 1
  )
)
echo.
echo This computer's local IPv4 address:
ipconfig | findstr /i "IPv4"
echo.
echo Leave this window open while playing.
echo Press Ctrl+C to stop the server.
echo.
"%PYTHON%" server.py
if errorlevel 1 (
  echo.
  echo The server stopped with an error.
  pause
)
