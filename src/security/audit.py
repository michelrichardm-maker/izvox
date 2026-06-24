"""
Journal d'audit append-only hash-chainé.

Format JSONL : un événement par ligne, chaque ligne contient le hash
SHA-256 du payload courant + le hash de l'événement précédent. Permet
de détecter :

- Suppression d'événements (la chaîne est brisée).
- Modification d'événements (le hash recalculé ne matche plus).
- Réordonnancement (mêmes raisons).

ATTENTION : sans secret partagé OU sans externalisation périodique du
dernier hash, un attaquant qui contrôle entièrement le fichier peut
toujours réécrire toute la chaîne de zéro. Le contrôle est tamper-
*evident* (visible), pas tamper-*proof* (impossible). Pour rendre le
log vraiment infalsifiable :

1. checkpointer le `last_hash` ailleurs (Slack, e-mail, autre serveur)
2. utiliser HMAC avec un secret externe (cf. roadmap Tier 3)

Important : on N'ÉCRIT JAMAIS le contenu des transcriptions ni des
traductions ici. Seulement des métadonnées (compteurs, longueurs,
hashes des artefacts utilisés). C'est un journal pour l'opérateur,
pas une transcription de la session.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64
HMAC_ENV_VAR = "IZVOX_AUDIT_KEY"


def _canonical_json(payload: Dict[str, Any]) -> str:
    """Sérialisation déterministe pour que le hash soit reproductible."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _compute_hash(payload: Dict[str, Any], prev_hash: str,
                  secret: Optional[bytes] = None) -> str:
    """Hash chaîné.

    Si `secret` est fourni, calcule HMAC-SHA256(secret, body) au lieu de
    SHA-256(body). Cela rend le log tamper-PROOF (et plus seulement
    tamper-evident) : un attaquant qui modifie le fichier ne peut pas
    recalculer un hash valide sans connaître le secret.

    Le secret peut venir de :
    - $IZVOX_AUDIT_KEY (chemin de migration le plus simple)
    - DPAPI (Windows) — TODO Tier 3+
    - TPM 2.0 PCR-bound key — TODO Tier 3+
    """
    body = _canonical_json(payload) + "|" + prev_hash
    if secret:
        return hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _get_audit_secret() -> Optional[bytes]:
    """Récupère le secret HMAC depuis l'environnement, ou None."""
    raw = os.environ.get(HMAC_ENV_VAR)
    if not raw:
        return None
    # Le secret doit être assez long pour être robuste.
    if len(raw) < 16:
        logger.warning(
            f"⚠ {HMAC_ENV_VAR} est trop court (<16 chars). "
            f"HMAC désactivé pour cette session."
        )
        return None
    return raw.encode("utf-8")


@dataclass
class AuditEvent:
    seq: int
    ts: str
    event: str
    data: Dict[str, Any] = field(default_factory=dict)
    prev_hash: str = GENESIS_HASH
    hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "ts": self.ts,
            "event": self.event,
            "data": self.data,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class AuditLog:
    """Journal append-only à hash chaîné.

    Usage :
        log = AuditLog("audit.log.jsonl")
        log.append("startup", {"version": "2.0.0"})
        log.append("model_loaded", {"name": "fr_FR-upmc-medium", "sha256_prefix": "9abb38..."})
        log.append("session_end", {"translations": 14, "redacted": True})
        log.close()
    """

    def __init__(self, path: Optional[Path | str] = None,
                 timestamp_provider=None,
                 secret: Optional[bytes] = None) -> None:
        """
        Args:
            path: chemin du fichier JSONL. None = in-memory uniquement.
            timestamp_provider: callable() -> str ISO8601. None = wall clock.
                Injecté pour les tests (les tests doivent pouvoir être
                déterministes).
            secret: clé HMAC. Si None, on lit $IZVOX_AUDIT_KEY. Si vide,
                fallback sur SHA-256 simple (tamper-evident seulement).
                Si fourni, le log devient tamper-PROOF (HMAC-SHA256).
        """
        self.path: Optional[Path] = Path(path) if path else None
        self._fh = None
        self._seq = 0
        self._last_hash = GENESIS_HASH
        self._timestamp_provider = timestamp_provider or _default_timestamp
        self._memory: List[AuditEvent] = []
        self._secret = secret if secret is not None else _get_audit_secret()

        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Reprend la chaîne s'il y a déjà un log
            if self.path.exists() and self.path.stat().st_size > 0:
                self._resume()
            self._fh = self.path.open("a", encoding="utf-8")

    def _resume(self) -> None:
        """Reprend le compteur et le hash depuis le dernier événement."""
        assert self.path is not None
        last_event: Optional[Dict[str, Any]] = None
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    last_event = json.loads(line)
                except json.JSONDecodeError:
                    continue
        if last_event:
            self._seq = int(last_event.get("seq", -1)) + 1
            self._last_hash = last_event.get("hash", GENESIS_HASH)

    def append(self, event: str, data: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """Ajoute un événement à la chaîne et le persiste si un fichier
        est configuré."""
        record = AuditEvent(
            seq=self._seq,
            ts=self._timestamp_provider(),
            event=event,
            data=dict(data or {}),
            prev_hash=self._last_hash,
        )
        payload_for_hash = {
            "seq": record.seq,
            "ts": record.ts,
            "event": record.event,
            "data": record.data,
        }
        record.hash = _compute_hash(
            payload_for_hash, record.prev_hash, self._secret
        )

        self._last_hash = record.hash
        self._seq += 1
        self._memory.append(record)

        if self._fh:
            self._fh.write(_canonical_json(record.to_dict()) + "\n")
            self._fh.flush()
        return record

    def events(self) -> List[AuditEvent]:
        """Retourne tous les événements (utile pour les tests)."""
        return list(self._memory)

    @property
    def last_hash(self) -> str:
        return self._last_hash

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None


# ---------------------------------------------------------------------------
# Vérification d'intégrité d'un log existant
# ---------------------------------------------------------------------------


@dataclass
class VerificationResult:
    ok: bool
    events_seen: int
    first_invalid_seq: Optional[int] = None
    reason: Optional[str] = None


def verify_audit_log(path: Path | str,
                     secret: Optional[bytes] = None) -> VerificationResult:
    """Recalcule la chaîne et vérifie que chaque hash matche.

    Args:
        path: fichier d'audit JSONL.
        secret: clé HMAC. Si None, on lit $IZVOX_AUDIT_KEY. Doit matcher
            celui utilisé à l'écriture, sinon tous les hashes seront
            invalides (ce qui est le comportement souhaité).

    Returns:
        VerificationResult avec ok=True si la chaîne est intacte, sinon
        first_invalid_seq pointe sur le 1ᵉʳ événement qui ne matche pas.
    """
    p = Path(path)
    if not p.exists():
        return VerificationResult(ok=False, events_seen=0, reason="file missing")

    used_secret = secret if secret is not None else _get_audit_secret()
    expected_prev = GENESIS_HASH
    seen = 0
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                return VerificationResult(
                    ok=False, events_seen=seen,
                    reason=f"invalid JSON at event #{seen}: {e}",
                )

            if record.get("prev_hash") != expected_prev:
                return VerificationResult(
                    ok=False, events_seen=seen,
                    first_invalid_seq=record.get("seq"),
                    reason="prev_hash mismatch (event modified or removed)",
                )

            payload = {
                "seq": record.get("seq"),
                "ts": record.get("ts"),
                "event": record.get("event"),
                "data": record.get("data") or {},
            }
            computed = _compute_hash(payload, record["prev_hash"], used_secret)
            if not hmac.compare_digest(computed, record.get("hash") or ""):
                return VerificationResult(
                    ok=False, events_seen=seen,
                    first_invalid_seq=record.get("seq"),
                    reason=(
                        "event payload was tampered "
                        "(or wrong HMAC secret)" if used_secret
                        else "event payload was tampered"
                    ),
                )

            expected_prev = record["hash"]
            seen += 1

    return VerificationResult(ok=True, events_seen=seen)


def _default_timestamp() -> str:
    # Évite Date.now()/datetime() lors de la résume d'un workflow ; ici
    # on est dans le main loop, donc c'est OK.
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
