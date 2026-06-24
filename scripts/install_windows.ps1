# =============================================================================
# izvox - Installation Windows turnkey (PowerShell)
#
# Equivalent de install_windows.bat avec la meme logique mais beaucoup plus
# propre grace aux primitives PowerShell.
#
# Usage :
#   powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# --- Auto-cd à la racine du projet ---
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Step {
    param([string]$Num, [string]$Msg)
    Write-Host ""
    Write-Host "[$Num/5] $Msg" -ForegroundColor Cyan
}

function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "    [INFO] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    [X] $msg" -ForegroundColor Red }

function Test-PythonCommand {
    param([string]$Cmd)
    try {
        $output = & $Cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$output" -match "Python\s+\d+\.\d+") {
            return "$output".Trim()
        }
    } catch {
        # Pas trouvé / redirecteur Microsoft Store qui jette une erreur
    }
    return $null
}

Write-Host "================================================================"
Write-Host "  INSTALLATION izvox - Traducteur Bidirectionnel"
Write-Host "================================================================"
Write-Host ""
Write-Host "Répertoire de travail : $RepoRoot"
Write-Host ""

# =============================================================================
# Étape 1 : détection Python
# =============================================================================
Write-Step "1" "Détection de Python..."

$PyCmd = $null
$PyVer = Test-PythonCommand "python"
if ($PyVer) {
    $PyCmd = "python"
} else {
    $PyVer = Test-PythonCommand "py"
    if ($PyVer) { $PyCmd = "py" }
}

if ($PyCmd) {
    Write-Ok "Python détecté : $PyVer (commande : $PyCmd)"
} else {
    Write-Info "Python non détecté sur ce système."
    Write-Host ""

    # =========================================================================
    # Étape 2 : installation automatique via winget
    # =========================================================================
    Write-Step "2" "Installation automatique via winget..."

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Err "winget n'est pas disponible sur ce système."
        Write-Host ""
        Write-Host "    Solutions :"
        Write-Host "      a) Mets à jour Windows (winget arrive avec Win10 1809+ / Win11)"
        Write-Host "      b) Installe Python manuellement depuis :"
        Write-Host "           https://www.python.org/downloads/"
        Write-Host "         IMPORTANT : coche 'Add Python to PATH' pendant l'installation."
        Write-Host "      c) Après install manuelle, relance ce script."
        exit 1
    }

    Write-Host "    Téléchargement et installation de Python 3.12..."
    & winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Err "L'installation Python via winget a échoué."
        exit 1
    }
    Write-Ok "Python 3.12 installé."

    # =========================================================================
    # Étape 3 : refresh du PATH dans la session courante
    # =========================================================================
    Write-Step "3" "Configuration du PATH pour cette session..."

    $PyUserDir    = "$env:LOCALAPPDATA\Programs\Python\Python312"
    $PyMachineDir = "$env:ProgramFiles\Python312"
    $env:Path = "$PyUserDir;$PyUserDir\Scripts;$PyMachineDir;$PyMachineDir\Scripts;$env:Path"

    $PyVer = Test-PythonCommand "python"
    if (-not $PyVer) {
        Write-Err "Python toujours introuvable après install."
        Write-Host "    Ferme cette fenêtre PowerShell, ouvre-en une nouvelle"
        Write-Host "    et relance install_windows.ps1."
        exit 1
    }
    $PyCmd = "python"
    Write-Ok "Python opérationnel : $PyVer"
}

# =============================================================================
# Étape 4 : création venv
# =============================================================================
Write-Step "4" "Création de l'environnement virtuel (venv)..."

if (Test-Path "venv\Scripts\python.exe") {
    Write-Info "venv existant détecté, on le réutilise."
} else {
    & $PyCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Impossible de créer le venv."
        exit 1
    }
    Write-Ok "venv créé."
}

& .\venv\Scripts\Activate.ps1
Write-Ok "venv activé."

# =============================================================================
# Étape 5 : installation des dépendances
# =============================================================================
Write-Step "5" "Installation des dépendances (compte 10-15 min)..."
Write-Host ""

Write-Host "    Mise à jour de pip..."
python -m pip install --upgrade pip

Write-Host ""
Write-Host "    Installation PyTorch (CUDA 11.8 si GPU NVIDIA, sinon CPU)..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
if ($LASTEXITCODE -ne 0) {
    Write-Host "    [WARN] CUDA échoué, fallback CPU..." -ForegroundColor Yellow
    pip install torch torchvision torchaudio
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Install PyTorch CPU échouée. Abandon."
        exit 1
    }
}

Write-Host ""
Write-Host "    Installation des dépendances izvox..."
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Err "Échec install requirements."
    exit 1
}

Write-Host ""
Write-Host "================================================================"
Write-Host "  INSTALLATION TERMINÉE" -ForegroundColor Green
Write-Host "================================================================"
Write-Host ""
Write-Host "Vérification :"
python tools\setup_check.py

Write-Host ""
Write-Host "--------------------------------------------------------------"
Write-Host "Étapes restantes (externes à ce script) :"
Write-Host ""
Write-Host "  1. Installer VB-Audio Virtual Cable (A + B)"
Write-Host "     voir : scripts\setup_vbcable.md"
Write-Host ""
Write-Host "  2. Lancer izvox :"
Write-Host "       .\scripts\run.ps1"
Write-Host ""
Write-Host "  3. Test sans matériel audio :"
Write-Host "       python tools\generate_test_wav.py --all"
Write-Host "       python -m src.main --input-file samples\sample_fr.wav ``"
Write-Host "                          --output-file out_en.wav"
Write-Host "--------------------------------------------------------------"
