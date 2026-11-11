@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 livynth_studio.py
) else (
    python livynth_studio.py
)
if errorlevel 1 (
    echo.
    echo LIVYNTH did not start. Install Python 3.10+ and Blender 4.5 LTS.
    pause
)