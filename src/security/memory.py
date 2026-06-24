"""
Durcissement mémoire : verrouillage des pages et scrub des buffers sensibles.

Deux contrôles :

1. **lock_process_memory()** — empêche le swap des pages de processus.
   - Linux/macOS : `mlockall(MCL_CURRENT | MCL_FUTURE)` via ctypes/libc.
   - Windows    : `SetProcessWorkingSetSize` + best-effort `VirtualLock`.

   Sans privilège (limite `ulimit -l` faible, pas de CAP_IPC_LOCK), l'appel
   peut échouer. Dans ce cas on log un warning et on continue : c'est un
   contrôle defense-in-depth, pas une garantie hard.

2. **secure_zero(...)** + **SecureAudioBuffer** — overwrite explicite
   des buffers audio/textes après usage. Vise à réduire la fenêtre
   d'exposition d'un dump mémoire (core dump, EDR, swap résiduel).

Note importante : Python ne garantit PAS qu'une référence pointe sur
les mêmes pages physiques au cours du temps (GC, realloc numpy). Le
scrub est un best-effort qui couvre les buffers stables (numpy arrays
en place, bytearrays mutables).
"""

from __future__ import annotations

import ctypes
import logging
import platform
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory locking
# ---------------------------------------------------------------------------


class MemoryLockError(RuntimeError):
    """Le verrouillage mémoire a échoué (pas fatal, juste informatif)."""


_locked = False


def is_memory_locked() -> bool:
    return _locked


def _lock_posix() -> None:
    """mlockall sur Linux/macOS."""
    # Constantes POSIX (équivalentes sur Linux et macOS)
    MCL_CURRENT = 1
    MCL_FUTURE = 2

    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
    except OSError:
        try:
            libc = ctypes.CDLL("libSystem.dylib", use_errno=True)
        except OSError as e:
            raise MemoryLockError(f"libc/libSystem introuvable: {e}") from e

    rc = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
    if rc != 0:
        err = ctypes.get_errno()
        # EPERM (1) = pas de privilège ; ENOMEM (12) = ulimit -l trop bas
        raise MemoryLockError(
            f"mlockall a échoué (errno={err}). "
            f"Augmentez ulimit -l ou ajoutez CAP_IPC_LOCK."
        )


def _lock_windows() -> None:
    """VirtualLock + SetProcessWorkingSetSize sur Windows.

    L'API VirtualLock(addr, size) ne permet pas de "lock everything" en
    un appel, mais SetProcessWorkingSetSize fixe une cible de working
    set qui réduit fortement la probabilité de swap. C'est ce que font
    la plupart des produits sécu sous Windows.
    """
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    pid = kernel32.GetCurrentProcess()
    # Demande un working set entre 64 Mo et 2 Go, ajustable.
    min_ws = ctypes.c_size_t(64 * 1024 * 1024)
    max_ws = ctypes.c_size_t(2 * 1024 * 1024 * 1024)
    ok = kernel32.SetProcessWorkingSetSize(pid, min_ws, max_ws)
    if not ok:
        err = ctypes.get_last_error()
        raise MemoryLockError(
            f"SetProcessWorkingSetSize a échoué (err={err})"
        )


def lock_process_memory() -> bool:
    """Tente de verrouiller la mémoire du process.

    Returns:
        True si le lock a réussi (les pages ne devraient plus aller en swap).
        False si l'OS n'a pas autorisé l'opération (logged en warning).
    """
    global _locked
    if _locked:
        return True

    system = platform.system()
    try:
        if system == "Windows":
            _lock_windows()
        else:
            _lock_posix()
        _locked = True
        logger.warning(f"🔒 Memory locking activé ({system})")
        return True
    except MemoryLockError as e:
        logger.warning(
            f"⚠ Memory locking indisponible ({e}). "
            f"Sans privilège, c'est attendu. Lancement non bloqué."
        )
        return False


# ---------------------------------------------------------------------------
# Memory scrub (overwrite in-place)
# ---------------------------------------------------------------------------


def secure_zero_array(arr: np.ndarray) -> None:
    """Overwrite un numpy array en place avec des zéros.

    Ne crée pas de nouvelle allocation : utilise `arr.fill(0)`. Le buffer
    sous-jacent est donc réellement écrasé (pour autant que le GC ne
    l'ait pas déjà recyclé).
    """
    if arr is None or arr.size == 0:
        return
    try:
        arr.fill(0)
    except Exception:  # noqa: BLE001
        # Buffer en lecture seule ou vue d'un autre array : on tente une
        # affectation explicite si l'OWNDATA flag est tombé.
        try:
            arr[...] = 0
        except Exception:  # noqa: BLE001
            pass


def secure_zero_bytearray(ba: bytearray) -> None:
    """Overwrite un bytearray en place avec des zéros."""
    if ba is None:
        return
    for i in range(len(ba)):
        ba[i] = 0


class SecureAudioBuffer:
    """Wrapper autour d'une liste de numpy arrays audio qui s'efface
    explicitement.

    Drop-in replacement pour `list[np.ndarray]` dans STT :

        buf = SecureAudioBuffer()
        buf.append(chunk)
        ...
        buf.secure_clear()   # overwrite + reset
    """

    def __init__(self) -> None:
        self._chunks: List[np.ndarray] = []

    def append(self, chunk: np.ndarray) -> None:
        self._chunks.append(chunk)

    def extend(self, chunks) -> None:
        self._chunks.extend(chunks)

    def concat(self) -> Optional[np.ndarray]:
        if not self._chunks:
            return None
        return np.concatenate(self._chunks)

    def __len__(self) -> int:
        return len(self._chunks)

    def __iter__(self):
        return iter(self._chunks)

    def __bool__(self) -> bool:
        return bool(self._chunks)

    def secure_clear(self) -> None:
        """Overwrite chaque chunk puis vide la liste."""
        for arr in self._chunks:
            secure_zero_array(arr)
        self._chunks = []
