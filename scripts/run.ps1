# Lancement rapide d'izvox sous Windows (PowerShell)

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[X] Environnement virtuel non trouvé." -ForegroundColor Red
    Write-Host "    Lancez d'abord: .\scripts\install_windows.ps1" -ForegroundColor Yellow
    exit 1
}

& .\venv\Scripts\Activate.ps1
python -m src.main @args
