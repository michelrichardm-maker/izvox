# Lancement rapide d'izvox - peut être lancé depuis n'importe quel CWD.

# Auto-cd à la racine du projet (parent de scripts/)
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[X] Environnement virtuel non trouvé." -ForegroundColor Red
    Write-Host "    Lance d'abord : .\scripts\install_windows.ps1" -ForegroundColor Yellow
    exit 1
}

& .\venv\Scripts\Activate.ps1
python -m src.main @args
