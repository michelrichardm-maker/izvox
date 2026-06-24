"""
Verrou egress (network lockdown).

Une fois les modèles chargés, izvox n'a plus aucun motif légitime
d'ouvrir une connexion sortante non-loopback. Ce module monkey-patche
`socket.socket.connect` (et la fonction de haut niveau
`socket.create_connection`) pour rejeter toute tentative vers une adresse
non-locale après l'appel à `lockdown_egress()`.

Conçu pour fonctionner avec urllib, requests, transformers, huggingface_hub,
torch.hub et tout ce qui passe par le socket Python de base.

Limites :
- Ne couvre PAS les processus enfants (faire confiance à os.fork est
  hors périmètre de ce module).
- Ne couvre PAS les binaires natifs qui ouvriraient leurs propres
  sockets (CTranslate2 statique, ONNX Runtime). En pratique, ces
  bibliothèques n'ouvrent pas de réseau après chargement.
- Le verrou est process-local et NE PERSISTE PAS à travers les exec.

Loopback autorisé (essentiel pour debugger, MCP, etc.) :
- 127.0.0.0/8
- ::1
- localhost (via DNS, donc on autorise aussi le résultat)
"""

from __future__ import annotations

import logging
import socket
from typing import Tuple

logger = logging.getLogger(__name__)


class NetworkLockdownError(PermissionError):
    """Levée quand une connexion non-loopback est tentée après lockdown."""


_LOOPBACK_HOSTS = {"localhost", "::1", "0.0.0.0", "::"}
_locked = False
_original_connect = None
_original_create_connection = None


def _is_loopback_addr(host: str) -> bool:
    """True si `host` est une adresse loopback acceptable."""
    if not host:
        return False
    if host in _LOOPBACK_HOSTS:
        return True
    # IPv4 loopback : 127.0.0.0/8
    if host.startswith("127."):
        return True
    # IPv6 loopback complet
    if host == "::1":
        return True
    # IPv4-mapped IPv6 loopback (::ffff:127.0.0.1)
    if host.startswith("::ffff:127."):
        return True
    return False


def _check_addr(address) -> None:
    """Lève NetworkLockdownError si l'adresse n'est pas loopback."""
    if isinstance(address, (tuple, list)) and len(address) >= 1:
        host = str(address[0])
    else:
        host = str(address)
    if not _is_loopback_addr(host):
        raise NetworkLockdownError(
            f"izvox network lockdown: blocked connect to {host!r} "
            f"(only loopback is allowed after lockdown)"
        )


def _patched_connect(self, address):  # noqa: ANN001
    _check_addr(address)
    return _original_connect(self, address)


def _patched_create_connection(
    address: Tuple[str, int],
    *args,
    **kwargs,
):
    _check_addr(address)
    return _original_create_connection(address, *args, **kwargs)


def lockdown_egress() -> None:
    """Active le verrou : toute connexion non-loopback échoue désormais.

    Idempotent : un second appel est un no-op.
    """
    global _locked, _original_connect, _original_create_connection
    if _locked:
        return

    _original_connect = socket.socket.connect
    _original_create_connection = socket.create_connection

    socket.socket.connect = _patched_connect  # type: ignore[assignment]
    socket.create_connection = _patched_create_connection  # type: ignore[assignment]

    _locked = True
    logger.warning(
        "🔒 Network lockdown activé : seules les connexions loopback sont autorisées"
    )


def is_locked_down() -> bool:
    """Retourne True si le lockdown est actif dans ce process."""
    return _locked


def _reset_for_tests() -> None:
    """USAGE TESTS UNIQUEMENT — restaure les sockets originaux."""
    global _locked, _original_connect, _original_create_connection
    if not _locked:
        return
    if _original_connect is not None:
        socket.socket.connect = _original_connect  # type: ignore[assignment]
    if _original_create_connection is not None:
        socket.create_connection = _original_create_connection  # type: ignore[assignment]
    _original_connect = None
    _original_create_connection = None
    _locked = False
