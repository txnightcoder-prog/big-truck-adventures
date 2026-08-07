@echo off
title Big Truck Adventures Video Editor - INSTALL & LAUNCH
color 0A

echo.
echo  =============================================================
echo   BIG TRUCK ADVENTURES - Video Editor
echo   100%% FREE  |  No watermarks  |  Runs locally on Windows
echo  =============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Python is not installed or not on PATH.
    echo.
    echo  Please download Python 3.10+ from: https://www.python.org/downloads/
    echo  IMPORTANT: During install, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo  [OK] Python found.
echo.
echo  Installing / updating dependencies...
echo.

:: Upgrade pip silently
python -m pip install --upgrade pip --quiet

:: Core GUI
echo  [1/6] Installing PyQt6...
pip install PyQt6 --quiet --upgrade

:: Video processing
echo  [2/6] Installing MoviePy...
pip install moviepy --quiet --upgrade

:: FFmpeg via imageio (needed by MoviePy)
echo  [3/6] Installing imageio with ffmpeg...
pip install "imageio[ffmpeg]" --quiet --upgrade

:: Image handling
echo  [4/6] Installing Pillow...
pip install Pillow --quiet --upgrade

:: Text-to-speech
echo  [5/6] Installing gTTS...
pip install gTTS --quiet --upgrade

:: HTTP requests
echo  [6/6] Installing requests...
pip install requests --quiet --upgrade

echo.
echo  =============================================================
echo   All dependencies installed successfully!
echo  =============================================================
echo.
echo  Creating project folders...
mkdir "%~dp0projects" 2>nul
mkdir "%~dp0exports"  2>nul
mkdir "%~dp0.cache"   2>nul
echo  [OK] Folders ready.
echo.

echo  Launching Big Truck Adventures Video Editor...
echo.
python "%~dp0video_editor.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] The editor crashed. See error above.
    echo  Common fixes:
    echo    - Re-run this file as Administrator
    echo    - Make sure Python 3.10+ is installed
    echo    - Run:  pip install PyQt6 moviepy Pillow gTTS
    pause
)
