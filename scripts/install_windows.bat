@echo off
setlocal EnableDelayedExpansion

echo ================================================================
echo   INSTALLATION - izvox Traducteur Bidirectionnel
echo ================================================================
echo.

REM Verification Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [X] Python non trouve.
    echo     Installez Python 3.10+ depuis https://www.python.org/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%I in ('python --version') do set PY_VER=%%I
echo [OK] Python detecte: %PY_VER%

REM Creation environnement virtuel
echo.
echo [INFO] Creation de l'environnement virtuel...
if exist venv (
    echo [INFO] Environnement existant detecte, on l'utilise.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [X] Impossible de creer l'environnement virtuel.
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat

REM Mise a jour pip
echo.
echo [INFO] Mise a jour de pip...
python -m pip install --upgrade pip

REM Detection GPU pour le choix du requirements
echo.
echo [INFO] Detection du materiel...
python -c "import sys; from urllib.request import urlopen" 2>nul

REM Installation PyTorch avec CUDA par defaut, fallback CPU
echo.
echo [INFO] Installation de PyTorch (CUDA 11.8)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 (
    echo [WARN] Installation CUDA echouee, fallback CPU...
    pip install torch torchvision torchaudio
)

REM Installation dependances communes
echo.
echo [INFO] Installation des dependances...
pip install -r requirements.txt

REM Verification
echo.
echo [INFO] Verification de l'installation...
python tools\setup_check.py

echo.
echo ================================================================
echo   INSTALLATION TERMINEE
echo ================================================================
echo.
echo Pour demarrer izvox:
echo    scripts\run.bat
echo.
echo Pour tester l'audio:
echo    python tools\audio_diagnostic.py
echo.
echo Pour pre-telecharger les modeles:
echo    python tools\download_models.py
echo.
pause
