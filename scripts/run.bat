@echo off
REM Lancement rapide d'izvox sous Windows

if not exist venv\Scripts\activate.bat (
    echo [X] Environnement virtuel non trouve.
    echo     Lancez d'abord: scripts\install_windows.bat
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m src.main %*
