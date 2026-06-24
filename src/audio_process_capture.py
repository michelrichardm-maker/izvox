"""
Process-level WASAPI loopback capture (Tier 3 — élimination de VB-Cable).

OBJECTIF : capturer directement l'audio d'un process spécifique (ex.
Teams) au lieu de passer par VB-Cable B (qui est multi-tenant). Permet
d'éliminer la fenêtre de fuite "n'importe quelle app peut sniffer le
câble" tout en gardant la latence de WASAPI natif.

ÉTAT ACTUEL : **stub**. Implémente l'API publique et la détection de
process, mais les appels COM réels (ActivateAudioInterfaceAsync avec
AUDIOCLIENT_ACTIVATION_PARAMS) ne sont pas encore connectés. Pour un MVP
opérationnel, voir la section "Implementation steps" plus bas.

RAISONS DE NE PAS L'IMPLÉMENTER MAINTENANT EN PYTHON :
- L'API ActivateAudioInterfaceAsync est asynchrone et nécessite un objet
  COM callback (IActivateAudioInterfaceCompletionHandler). C'est lourd
  en pur Python via ctypes — ~300-500 lignes de COM scaffolding.
- Aucune bibliothèque Python ne l'expose proprement (pyaudiowpatch
  s'arrête au loopback "device-level", pas "process-level").
- Le développeur ne dispose pas d'un environnement Windows pour valider
  l'implémentation. Risque de régression silencieuse.

ROADMAP D'IMPLÉMENTATION (par ordre) :
1. Wrapper C++ minimaliste compilé en .pyd qui expose
   `start_process_loopback(pid, callback) -> Stream`.
2. OU bind direct via `comtypes` (plus haut niveau que ctypes pur).
3. Tests sur un poste Windows 10 1903+ avec un process cible factice
   (ex. mpv jouant un fichier audio).
4. Intégration dans pipeline.py via une `AudioConfig.incoming_source` à
   trois valeurs : "vbcable" (actuel), "process" (nouveau), "auto".
5. Au boot, si "process", on cherche teams.exe / ms-teams.exe et on
   accroche son output. Fallback explicite vers vbcable si absent.

CE QUE CE FICHIER OFFRE AUJOURD'HUI :
- L'API stable que le pipeline appellera (find_process_pid, capture
  context manager) → pas de changement futur côté pipeline.py.
- Une détection portable du PID Teams.
- Un message d'erreur clair sur Linux et sur les Windows trop anciens.

API publique (stable) :
    pid = find_target_process_pid(["teams", "ms-teams"])
    with process_loopback_capture(pid, sample_rate=16000) as stream:
        while running:
            chunk = stream.read(1024)
            ...
"""

from __future__ import annotations

import logging
import platform
import sys
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


class ProcessLoopbackNotSupported(RuntimeError):
    """L'API process-level WASAPI loopback n'est pas disponible.

    Raisons possibles :
    - OS non-Windows
    - Windows < 10 build 1903 (avant Application Loopback API)
    - Implémentation Python non encore finalisée
    """


def find_target_process_pid(name_candidates: Iterable[str]) -> Optional[int]:
    """Cherche le 1ᵉʳ process tournant qui matche un des noms candidats.

    Args:
        name_candidates: liste de noms (sans extension). Comparaison
            insensible à la casse. Ex. ["teams", "ms-teams", "ms-teamsuwp"]

    Returns:
        PID du process trouvé, ou None.
    """
    try:
        import psutil  # type: ignore
    except ImportError:
        logger.warning("psutil non installé : impossible de chercher le PID")
        return None

    candidates_lower = {n.lower() for n in name_candidates}
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            stem = name.split(".")[0]
            if stem in candidates_lower:
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


# Noms de process Teams connus selon les versions
TEAMS_PROCESS_NAMES: List[str] = [
    "teams",         # Teams classique pre-2022
    "ms-teams",      # Teams 2.0+
    "ms-teamsuwp",   # Teams MSIX/UWP
]


def find_teams_pid() -> Optional[int]:
    """Helper : retourne le PID de Microsoft Teams s'il tourne."""
    return find_target_process_pid(TEAMS_PROCESS_NAMES)


# ---------------------------------------------------------------------------
# Stub de capture — laissé volontairement non-implémenté
# ---------------------------------------------------------------------------


class ProcessLoopbackStream:
    """Interface stable. Implémentation à finaliser (voir docstring du
    module)."""

    def read(self, frames: int) -> bytes:
        raise ProcessLoopbackNotSupported(
            "Process-level WASAPI loopback Python binding not yet implemented. "
            "See src/audio_process_capture.py docstring for the roadmap."
        )

    def close(self) -> None:
        pass


def process_loopback_capture(
    pid: int,
    sample_rate: int = 16000,
    chunk_size: int = 1024,
) -> ProcessLoopbackStream:
    """Ouvre un stream de capture loopback ciblé sur `pid`.

    NOT YET IMPLEMENTED. Lève ProcessLoopbackNotSupported.

    L'implémentation devra :
    1. CoInitialize sur le thread.
    2. ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, ...)
       avec AUDIOCLIENT_ACTIVATION_PARAMS{
           ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK,
           ProcessLoopbackParams = {
               TargetProcessId = pid,
               ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE,
           }
       }
    3. Attendre le callback IActivateAudioInterfaceCompletionHandler.
    4. IAudioClient::Initialize(AUDCLNT_STREAMFLAGS_LOOPBACK, …)
    5. IAudioCaptureClient::GetBuffer → bytes.

    Args:
        pid: PID du process source.
        sample_rate: souhaité (l'API peut refuser et imposer le format
            mixé du processus).
        chunk_size: taille des chunks à retourner.
    """
    if platform.system() != "Windows":
        raise ProcessLoopbackNotSupported(
            f"Process-level loopback est Windows-only. OS détecté : "
            f"{platform.system()}"
        )
    if sys.getwindowsversion().build < 18362 if hasattr(sys, "getwindowsversion") else True:
        raise ProcessLoopbackNotSupported(
            "Process-level loopback requiert Windows 10 build 18362 (1903) "
            "ou supérieur."
        )

    raise ProcessLoopbackNotSupported(
        "Process-level WASAPI loopback Python binding not yet implemented. "
        "Voir src/audio_process_capture.py pour la roadmap."
    )


def is_process_loopback_supported() -> bool:
    """Vraie si l'API est utilisable maintenant.

    Aujourd'hui : False partout (stub). Quand l'implémentation sera
    finalisée, retournera True sur Windows 10 1903+ avec les bindings
    présents.
    """
    return False
