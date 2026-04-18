@echo off
title EDITH Installer
color 0b
echo.
echo  ================================================
echo   E.D.I.T.H — AI Assistant Installer
echo   Enhanced Defence Intelligence Tactical Hub
echo  ================================================
echo.
echo  [1/5] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo  ERROR: Python not found! Install Python 3.8+ from python.org
    pause
    exit /b 1
)
echo.
echo  [2/5] Installing core packages...
pip install pyttsx3 SpeechRecognition pyaudio wikipedia requests psutil pyautogui --quiet
echo.
echo  [3/5] All packages installed!
echo.
echo  [4/5] Launching EDITH...
echo.
python jarvis_edith.py
echo.
echo  [5/5] EDITH has shut down. Goodbye!
pause
