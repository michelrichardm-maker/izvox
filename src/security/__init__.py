"""
Contrôles zero-trust pour izvox.

Sous-modules :
- redaction : helpers pour masquer le contenu textuel dans les logs.
- network   : verrou egress (post-init, plus aucune connexion non-loopback).
- manifest  : vérification des hashes SHA-256 des modèles téléchargés.
"""

from .manifest import (
    ManifestError,
    ManifestMismatchError,
    UnknownArtifactError,
    load_manifest,
    sha256_file,
    verify_artifact,
    verify_artifact_from_manifest,
)
from .network import NetworkLockdownError, is_locked_down, lockdown_egress
from .redaction import maybe_redact, redact

__all__ = [
    "redact",
    "maybe_redact",
    "lockdown_egress",
    "is_locked_down",
    "NetworkLockdownError",
    "load_manifest",
    "sha256_file",
    "verify_artifact",
    "verify_artifact_from_manifest",
    "ManifestError",
    "ManifestMismatchError",
    "UnknownArtifactError",
]
