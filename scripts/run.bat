@echo off
REM Lancement rapide d'izvox - peut etre lance depuis n'importe quel CWD.

REM Auto-cd a la racine du projet (parent de scripts/)
cd /d "%~dp0\.."

if not exist venv\Scripts\activate.bat (
    echo [X] Environnement virtuel non trouve.
    echo     Lance d'abord : scripts\install_windows.bat
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m src.main %*
