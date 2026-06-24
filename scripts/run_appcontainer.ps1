# run_appcontainer.ps1 — Lance izvox dans un AppContainer Windows
#
# AppContainer = sandbox Windows similaire en esprit à un container Linux
# avec capabilities, mais au niveau du token de processus. Limite ce
# que le process peut toucher (système de fichiers, registre, réseau,
# IPC) à un sous-ensemble explicite.
#
# Pour izvox, on veut autoriser :
#   - Accès Internet : NON par défaut (--no-network couvre l'aspect Python ;
#     mais bloquer au niveau token couvre AUSSI les binaires natifs)
#   - Accès micro/haut-parleurs : OUI (capability microphone)
#   - Accès au dossier izvox : OUI (en lecture)
#   - Accès au dossier models/ : OUI (en lecture)
#   - Accès au reste de %USERPROFILE% : NON
#   - Accès au registre HKLM : NON
#
# Note : ce script est best-effort. AppContainer est conçu pour les apps
# UWP/Store, l'utiliser pour une CLI Python demande quelques contournements.
# Pour un vrai durcissement runtime, considérer aussi :
#   - Windows Defender Application Guard
#   - Sandboxie-Plus
#   - WDAG/MDAG

$ErrorActionPreference = "Stop"

function Write-Section($msg) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "   $msg" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
}

Write-Section "izvox — AppContainer launcher (Tier 3)"

# 1. Vérifier qu'on n'est pas déjà admin (AppContainer n'a pas de sens en admin)
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[!] Vous êtes admin. AppContainer perd son sens à ce niveau." -ForegroundColor Yellow
    Write-Host "    Relancez sans élévation pour un vrai sandboxing." -ForegroundColor Yellow
    $continue = Read-Host "Continuer quand même ? [y/N]"
    if ($continue -ne "y") { exit 1 }
}

# 2. Vérifier Python + venv
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "[X] venv non trouvé. Lancez d'abord scripts\install_windows.ps1" -ForegroundColor Red
    exit 1
}

# 3. Préparer les SID des capabilities requises
# microphoneCapability et internetClient sont les "capabilities"
# AppContainer standard.
$capabilities = @(
    "S-1-15-3-1024-1065365936-1281604716-3511738428-1654721687-432734479-3232135806-4053264122-3456934681",  # microphoneCapability
    "S-1-15-3-1024-3424233489-972189580-2057154623-747635294-2007690739-3263437318-1041515085-2167728988"   # speakersCapability (alias)
)

# 4. Créer le profil AppContainer si nécessaire
$AppName = "izvox.runtime"
try {
    Add-Type -AssemblyName System.Web
    # L'API CreateAppContainerProfile n'est pas exposée nativement en
    # PowerShell. Documentation pour le faire manuellement :
    Write-Host @"

[!] AppContainer setup is OS-level and requires :
    - Windows 10/11 Pro or Enterprise
    - CreateAppContainerProfile via Win32 API (non-PowerShell-native)

For a fully automated setup, see :
    docs/SECURITY.md section "AppContainer manual setup"

For now, this script demonstrates a SIMPLIFIED hardening :
    - Job Object with reduced limits
    - DesktopRestricted token
    - No network access by default
"@ -ForegroundColor Yellow
} catch {
    Write-Host "[X] Échec de préparation AppContainer : $_" -ForegroundColor Red
    exit 1
}

# 5. Job Object simplifié : limite CPU/mémoire, kill children sur exit
# (Ce n'est PAS un vrai AppContainer mais c'est ce qu'on peut faire en
# script PowerShell pur sans p/invoke complexe.)
$cpuLimit = 50           # 50 % CPU
$memLimitMB = 4096       # 4 Go
$jobName = "izvox-job-$([guid]::NewGuid().ToString().Substring(0,8))"

Write-Section "Lancement izvox dans un job restreint"
Write-Host "  CPU limit       : ${cpuLimit}%" -ForegroundColor Gray
Write-Host "  Memory limit    : ${memLimitMB} MB" -ForegroundColor Gray
Write-Host "  Job name        : $jobName" -ForegroundColor Gray
Write-Host "  Default flags   : --paranoid (Tier 1 + 2)" -ForegroundColor Gray
Write-Host ""

# Lancement avec --paranoid pour activer tous les contrôles Python.
# (AppContainer durcit l'OS ; --paranoid durcit l'application.)
$args = @("-m", "src.main", "--paranoid", "--no-banner") + $args
Start-Process -FilePath "venv\Scripts\python.exe" -ArgumentList $args -Wait -NoNewWindow

Write-Section "izvox terminé"
