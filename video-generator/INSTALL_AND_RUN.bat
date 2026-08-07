@echo off
echo ================================================
echo   BIG TRUCK ADVENTURES - Video Generator Setup
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing required packages...
pip install moviepy Pillow gTTS numpy requests
echo.

echo [2/3] Creating output folders...
if not exist "output" mkdir output
if not exist "temp_audio" mkdir temp_audio
if not exist "assets" mkdir assets
echo.

echo [3/3] Ready! Running preview of Episode 1...
echo.
python generate_video.py --episode 1 --preview
echo.
echo ================================================
echo   Preview images saved to: output\E01_preview\
echo   Open that folder to see all 10 scenes!
echo.
echo   To generate the FULL VIDEO run:
echo   python generate_video.py --episode 1
echo ================================================
pause
