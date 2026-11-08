@echo off
cd /d "%~dp0"
set "PYTHON=python"
if exist "%USERPROFILE%\miniconda3\python.exe" set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
echo Installing Blue Blood requirements. This may take a few minutes...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation failed. Check that Python and internet access are available.
  pause
  exit /b 1
)
echo.
echo Blue Blood is ready to launch with Play Blue Blood.bat.
pause
