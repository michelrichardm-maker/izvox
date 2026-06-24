"""Tests pour le mode HMAC de l'audit log (Tier 3)."""

import json
import os

import pytest

from src.security.audit import (
    AuditLog,
    HMAC_ENV_VAR,
    verify_audit_log,
)


def _ts():
    counter = iter(range(1_000_000))
    return lambda: f"2026-06-24T00:00:{next(counter):02d}Z"


SECRET = b"this-is-a-long-enough-secret-key"
OTHER_SECRET = b"some-other-long-enough-secret-key"


def test_hmac_chain_valid_with_correct_secret(tmp_path):
    p = tmp_path / "a.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts(), secret=SECRET)
    for i in range(3):
        log.append(f"evt-{i}", {"n": i})
    log.close()

    result = verify_audit_log(p, secret=SECRET)
    assert result.ok is True
    assert result.events_seen == 3


def test_hmac_chain_invalid_with_wrong_secret(tmp_path):
    p = tmp_path / "a.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts(), secret=SECRET)
    log.append("evt", {"n": 1})
    log.close()

    result = verify_audit_log(p, secret=OTHER_SECRET)
    assert result.ok is False
    assert "tamper" in (result.reason or "").lower() or "secret" in (result.reason or "").lower()


def test_hmac_chain_invalid_when_log_written_without_secret(tmp_path):
    """Un log écrit en SHA256 plain ne se vérifie pas avec une clé HMAC
    (et vice-versa)."""
    p = tmp_path / "a.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts(), secret=None)
    log.append("evt", {"n": 1})
    log.close()

    result = verify_audit_log(p, secret=SECRET)
    assert result.ok is False


def test_hmac_log_resists_payload_tampering(tmp_path):
    """Même si on modifie un payload, sans le secret on ne peut pas
    fabriquer un hash valide."""
    p = tmp_path / "a.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts(), secret=SECRET)
    log.append("a")
    log.append("b")
    log.close()

    lines = p.read_text().strip().split("\n")
    parsed = [json.loads(line) for line in lines]
    parsed[0]["data"] = {"tampered": True}
    # Si l'attaquant n'a pas le secret, il ne peut pas recalculer le hash.
    # On laisse l'ancien hash : la vérification doit échouer.
    p.write_text("\n".join(json.dumps(e) for e in parsed) + "\n")

    result = verify_audit_log(p, secret=SECRET)
    assert result.ok is False


def test_env_variable_picks_up_secret(monkeypatch, tmp_path):
    monkeypatch.setenv(HMAC_ENV_VAR, "an-env-var-secret-1234567890")
    p = tmp_path / "a.jsonl"
    # secret=None → doit lire depuis l'env
    log = AuditLog(path=p, timestamp_provider=_ts(), secret=None)
    assert log._secret is not None
    log.append("evt")
    log.close()

    # Vérification avec lecture env aussi
    result = verify_audit_log(p, secret=None)
    assert result.ok is True


def test_short_env_secret_is_rejected(monkeypatch, tmp_path):
    """Une clé HMAC de moins de 16 chars doit être ignorée (warning)."""
    monkeypatch.setenv(HMAC_ENV_VAR, "short")
    log = AuditLog(path=tmp_path / "a.jsonl", timestamp_provider=_ts(), secret=None)
    # Fallback : pas de HMAC
    assert log._secret is None
