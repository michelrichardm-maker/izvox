# Installation izvox - PowerShell
# Lancer avec: powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1

$ErrorActionPreference = "Stop"

function Write-Section($msg) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "   $msg" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
}

Write-Section "INSTALLATION - izvox Traducteur Bidirectionnel"

# Vérification Python
try {
    $pyVersion = & python --version 2>&1
    Write-Host "[OK] Python détecté: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[X] Python non trouvé. Installez Python 3.10+ depuis https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Création environnement virtuel
Write-Host ""
if (Test-Path "venv") {
    Write-Host "[INFO] Environnement venv existant, on l'utilise." -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Création de l'environnement virtuel..." -ForegroundColor Cyan
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] Impossible de créer l'environnement virtuel." -ForegroundColor Red
        exit 1
    }
}

# Activation
& .\venv\Scripts\Activate.ps1

# Mise à jour pip
Write-Host ""
Write-Host "[INFO] Mise à jour de pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# PyTorch CUDA
Write-Host ""
Write-Host "[INFO] Installation de PyTorch (CUDA 11.8)..." -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Installation CUDA échouée, fallback CPU..." -ForegroundColor Yellow
    pip install torch torchvision torchaudio
}

# Dépendances
Write-Host ""
Write-Host "[INFO] Installation des dépendances..." -ForegroundColor Cyan
pip install -r requirements.txt

# Vérification
Write-Host ""
Write-Host "[INFO] Vérification de l'installation..." -ForegroundColor Cyan
python tools\setup_check.py

Write-Section "INSTALLATION TERMINÉE"

Write-Host ""
Write-Host "Pour démarrer izvox:" -ForegroundColor Green
Write-Host "   .\scripts\run.ps1"
Write-Host ""
Write-Host "Pour tester l'audio:" -ForegroundColor Green
Write-Host "   python tools\audio_diagnostic.py"
Write-Host ""
Write-Host "Pour pré-télécharger les modèles:" -ForegroundColor Green
Write-Host "   python tools\download_models.py"
Write-Host ""
