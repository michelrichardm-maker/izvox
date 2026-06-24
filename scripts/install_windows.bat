@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM  izvox - Installation Windows turnkey
REM
REM  Ce script :
REM    1. Se positionne automatiquement a la racine du projet
REM       (peu importe d'ou il est lance)
REM    2. Detecte python ou py
REM    3. S'il manque, installe Python 3.12 via winget automatiquement
REM    4. Configure le PATH pour la session courante
REM    5. Cree le venv, installe les deps, lance le setup_check
REM ============================================================================

REM --- Auto-cd a la racine du projet ---
cd /d "%~dp0\.."

echo ================================================================
echo   INSTALLATION izvox - Traducteur Bidirectionnel
echo ================================================================
echo.
echo Repertoire de travail : %CD%
echo.

REM ============================================================================
REM  Etape 1 : detection Python
REM ============================================================================
echo [1/5] Detection de Python...

set "PYTHON_CMD="
set "PY_VER="

REM Essai 1 : `python` mais on filtre le redirecteur Microsoft Store
where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%v in ('python --version 2^>nul') do set "PY_VER=%%v"
    if defined PY_VER (
        echo !PY_VER! | findstr /b /c:"Python " >nul
        if not errorlevel 1 (
            set "PYTHON_CMD=python"
        )
    )
)

REM Essai 2 : `py` (Python Launcher)
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%v in ('py --version 2^>nul') do set "PY_VER=%%v"
        if defined PY_VER set "PYTHON_CMD=py"
    )
)

if defined PYTHON_CMD (
    echo     [OK] Python detecte : !PY_VER!
    echo     Commande : !PYTHON_CMD!
    goto :python_ready
)

echo     [INFO] Python non detecte sur ce systeme.
echo.

REM ============================================================================
REM  Etape 2 : installation automatique via winget
REM ============================================================================
echo [2/5] Installation automatique via winget...

where winget >nul 2>&1
if errorlevel 1 (
    echo     [X] winget n'est pas disponible sur ce systeme.
    echo.
    echo     Solutions :
    echo       a^) Met a jour Windows ^(winget arrive avec Win10 1809+ / Win11^)
    echo       b^) Installe Python manuellement depuis :
    echo            https://www.python.org/downloads/
    echo          IMPORTANT : coche "Add Python to PATH" pendant l'installation.
    echo       c^) Apres install manuelle, relance ce script.
    echo.
    pause
    exit /b 1
)

echo     Telechargement et installation de Python 3.12...
winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo     [X] L'installation Python via winget a echoue.
    echo     Verifie ta connexion et tes droits d'utilisateur.
    pause
    exit /b 1
)
echo     [OK] Python 3.12 installe.

REM ============================================================================
REM  Etape 3 : configuration du PATH dans la session courante
REM ============================================================================
echo [3/5] Configuration du PATH pour cette session...

REM winget installe par defaut en user-scope :
REM   %LOCALAPPDATA%\Programs\Python\Python312\python.exe
REM Ajout aussi du scope machine au cas ou.
set "PY_USER_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
set "PY_MACHINE_DIR=%ProgramFiles%\Python312"
set "PATH=%PY_USER_DIR%;%PY_USER_DIR%\Scripts;%PY_MACHINE_DIR%;%PY_MACHINE_DIR%\Scripts;%PATH%"

REM Re-verification
where python >nul 2>&1
if errorlevel 1 (
    echo     [X] Python toujours introuvable apres install.
    echo     Ferme cette fenetre PowerShell/cmd, ouvre-en une nouvelle
    echo     et relance install_windows.bat.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python --version 2^>nul') do set "PY_VER=%%v"
set "PYTHON_CMD=python"
echo     [OK] Python operationnel : !PY_VER!

:python_ready
echo.

REM ============================================================================
REM  Etape 4 : creation du venv
REM ============================================================================
echo [4/5] Creation de l'environnement virtuel ^(venv^)...

if exist venv\Scripts\python.exe (
    echo     [INFO] venv existant detecte, on le reutilise.
) else (
    !PYTHON_CMD! -m venv venv
    if errorlevel 1 (
        echo     [X] Impossible de creer le venv.
        echo     Verifie que tu as les droits d'ecriture sur %CD%.
        pause
        exit /b 1
    )
    echo     [OK] venv cree.
)

call venv\Scripts\activate.bat
echo     [OK] venv active.
echo.

REM ============================================================================
REM  Etape 5 : installation des dependances Python
REM ============================================================================
echo [5/5] Installation des dependances ^(compte 10-15 min^)...
echo.

echo     Mise a jour de pip...
python -m pip install --upgrade pip

echo.
echo     Installation PyTorch ^(CUDA 11.8 si GPU NVIDIA, sinon CPU^)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 (
    echo     [WARN] Install CUDA echouee, fallback vers la version CPU...
    pip install torch torchvision torchaudio
    if errorlevel 1 (
        echo     [X] Install PyTorch CPU echouee aussi. Abandon.
        pause
        exit /b 1
    )
)

echo.
echo     Installation des dependances izvox...
pip install -r requirements.txt
if errorlevel 1 (
    echo     [X] Echec install requirements.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   INSTALLATION TERMINEE
echo ================================================================
echo.
echo Verification de l'installation :
python tools\setup_check.py

echo.
echo --------------------------------------------------------------
echo Etapes restantes ^(externes a ce script^) :
echo.
echo   1. Installer VB-Audio Virtual Cable ^(A + B^)
echo      voir : scripts\setup_vbcable.md
echo.
echo   2. Lancer izvox :
echo        .\scripts\run.bat
echo.
echo   3. Test sans materiel audio :
echo        python tools\generate_test_wav.py --all
echo        python -m src.main --input-file samples\sample_fr.wav ^^
echo                           --output-file out_en.wav
echo --------------------------------------------------------------
echo.
pause
