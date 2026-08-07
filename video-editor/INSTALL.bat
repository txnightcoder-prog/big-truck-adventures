@echo off
echo ================================================
echo   BIG TRUCK ADVENTURES - Video Editor Setup
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing required packages...
pip install "moviepy>=1.0.3" "Pillow>=10.4.0" "gTTS>=2.5.3" "numpy>=1.26.4" "requests>=2.32.3" "PyQt6>=6.7.0" "imageio>=2.34.2" "imageio-ffmpeg>=0.5.1"
echo.

echo [2/3] Creating output folders...
if not exist "projects" mkdir projects
if not exist "exports" mkdir exports
if not exist ".cache" mkdir .cache
echo.

echo [3/3] Launching Big Truck Adventures Video Editor...
set PYTHONUTF8=1
python video_editor.py
