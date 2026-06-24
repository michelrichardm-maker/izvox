"""
Contrôles zero-trust pour izvox.

Sous-modules :
- redaction : helpers pour masquer le contenu textuel dans les logs.
- network   : verrou egress (post-init, plus aucune connexion non-loopback).
- manifest  : vérification des hashes SHA-256 des modèles téléchargés.
"""

from .audit import AuditEvent, AuditLog, VerificationResult, verify_audit_log
from .manifest import (
    ManifestError,
    ManifestMismatchError,
    UnknownArtifactError,
    load_manifest,
    sha256_file,
    verify_artifact,
    verify_artifact_from_manifest,
)
from .memory import (
    MemoryLockError,
    SecureAudioBuffer,
    is_memory_locked,
    lock_process_memory,
    secure_zero_array,
    secure_zero_bytearray,
)
from .network import NetworkLockdownError, is_locked_down, lockdown_egress
from .redaction import maybe_redact, redact

__all__ = [
    # redaction
    "redact",
    "maybe_redact",
    # network
    "lockdown_egress",
    "is_locked_down",
    "NetworkLockdownError",
    # manifest
    "load_manifest",
    "sha256_file",
    "verify_artifact",
    "verify_artifact_from_manifest",
    "ManifestError",
    "ManifestMismatchError",
    "UnknownArtifactError",
    # memory
    "lock_process_memory",
    "is_memory_locked",
    "MemoryLockError",
    "SecureAudioBuffer",
    "secure_zero_array",
    "secure_zero_bytearray",
    # audit
    "AuditLog",
    "AuditEvent",
    "VerificationResult",
    "verify_audit_log",
]
