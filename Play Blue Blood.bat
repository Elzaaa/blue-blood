@echo off
cd /d "%~dp0"
if exist "%USERPROFILE%\miniconda3\python.exe" (
  "%USERPROFILE%\miniconda3\python.exe" main.py
) else (
  python main.py
)
if errorlevel 1 (
  echo.
  echo The game could not start. Copy this message and send it for help.
  pause
)
