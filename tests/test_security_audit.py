"""Tests pour src/security/audit.py — journal hash-chainé."""

import json

import pytest

from src.security.audit import (
    GENESIS_HASH,
    AuditLog,
    verify_audit_log,
)


# Itérateur déterministe pour des timestamps reproductibles
def _ts_provider():
    counter = iter(range(1_000_000))
    return lambda: f"2026-06-24T00:00:{next(counter):02d}Z"


# ---------------------------------------------------------------------------
# Chaining
# ---------------------------------------------------------------------------


def test_first_event_uses_genesis_hash():
    log = AuditLog(path=None, timestamp_provider=_ts_provider())
    ev = log.append("startup", {"version": "test"})
    assert ev.prev_hash == GENESIS_HASH
    assert ev.seq == 0
    assert len(ev.hash) == 64


def test_chain_links_correctly():
    log = AuditLog(path=None, timestamp_provider=_ts_provider())
    e0 = log.append("a")
    e1 = log.append("b")
    e2 = log.append("c")
    assert e1.prev_hash == e0.hash
    assert e2.prev_hash == e1.hash
    assert e0.seq == 0 and e1.seq == 1 and e2.seq == 2


def test_event_hash_changes_with_data():
    """Deux événements avec data différente doivent avoir des hashes
    différents."""
    log_a = AuditLog(path=None, timestamp_provider=_ts_provider())
    log_b = AuditLog(path=None, timestamp_provider=_ts_provider())
    a = log_a.append("evt", {"x": 1})
    b = log_b.append("evt", {"x": 2})
    assert a.hash != b.hash


# ---------------------------------------------------------------------------
# Persistence + verify_audit_log
# ---------------------------------------------------------------------------


def test_persists_to_jsonl(tmp_path):
    p = tmp_path / "audit.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts_provider())
    log.append("startup")
    log.append("model_loaded", {"name": "fr_FR-upmc-medium"})
    log.append("shutdown")
    log.close()

    lines = p.read_text().strip().split("\n")
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["event"] == "startup"
    assert parsed[1]["data"]["name"] == "fr_FR-upmc-medium"


def test_verify_clean_chain(tmp_path):
    p = tmp_path / "audit.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts_provider())
    for i in range(5):
        log.append(f"evt-{i}", {"seq": i})
    log.close()

    result = verify_audit_log(p)
    assert result.ok is True
    assert result.events_seen == 5


def test_verify_detects_payload_tampering(tmp_path):
    p = tmp_path / "audit.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts_provider())
    log.append("a")
    log.append("b")
    log.append("c")
    log.close()

    # Tampe l'événement #1 (changement de event payload)
    lines = p.read_text().strip().split("\n")
    parsed = [json.loads(line) for line in lines]
    parsed[1]["event"] = "TAMPERED"
    p.write_text("\n".join(json.dumps(e) for e in parsed) + "\n")

    result = verify_audit_log(p)
    assert result.ok is False
    assert "tamper" in (result.reason or "").lower()


def test_verify_detects_removed_event(tmp_path):
    p = tmp_path / "audit.jsonl"
    log = AuditLog(path=p, timestamp_provider=_ts_provider())
    log.append("a")
    log.append("b")
    log.append("c")
    log.close()

    # Supprime l'événement du milieu
    lines = p.read_text().strip().split("\n")
    p.write_text(lines[0] + "\n" + lines[2] + "\n")

    result = verify_audit_log(p)
    assert result.ok is False
    assert "prev_hash" in (result.reason or "")


def test_verify_missing_file(tmp_path):
    result = verify_audit_log(tmp_path / "absent.jsonl")
    assert result.ok is False
    assert "missing" in (result.reason or "")


def test_resume_continues_chain(tmp_path):
    """Un second AuditLog ouvert sur le même fichier doit reprendre la
    chaîne (pas réinitialiser à seq=0)."""
    p = tmp_path / "audit.jsonl"
    log1 = AuditLog(path=p, timestamp_provider=_ts_provider())
    log1.append("a")
    log1.append("b")
    log1.close()

    log2 = AuditLog(path=p, timestamp_provider=_ts_provider())
    e = log2.append("c")
    log2.close()
    assert e.seq == 2

    result = verify_audit_log(p)
    assert result.ok is True
    assert result.events_seen == 3


def test_does_not_log_text_content():
    """L'API n'accepte pas le texte brut au top-level ; tout passe par
    `data`. Vérification documentaire : on s'attend à ce que les callers
    passent des métadonnées."""
    log = AuditLog(path=None, timestamp_provider=_ts_provider())
    # On ne devrait JAMAIS faire ça (mais c'est techniquement possible) :
    e = log.append("translation_done", {"chars": 14, "words": 3})
    # Le test vérifie qu'on a juste ce qu'on veut, pas un mot sensible.
    assert "chars" in e.data
    assert "secret" not in str(e.data)
