"""Tests pour les contrôles zero-trust (Palier 1)."""

import hashlib
import json
import socket
from pathlib import Path

import pytest

from src.security import (
    ManifestMismatchError,
    UnknownArtifactError,
    is_locked_down,
    load_manifest,
    redact,
    sha256_file,
    verify_artifact,
)
from src.security.network import (
    NetworkLockdownError,
    _reset_for_tests,
    lockdown_egress,
)
from src.security.redaction import maybe_redact
from src.security.manifest import verify_artifact_from_manifest


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def test_redact_basic():
    assert redact("Bonjour le monde", "fr") == "[FR 16 chars / 3 words]"
    assert redact("Hello", "en") == "[EN 5 chars / 1 words]"


def test_redact_handles_none_and_empty():
    assert "none" in redact(None, "fr").lower()
    assert "empty" in redact("", "fr").lower()
    assert "empty" in redact("   ", "fr").lower()


def test_redact_does_not_leak_content():
    secret = "Le code de coffre est 1234"
    out = redact(secret, "fr")
    assert "1234" not in out
    assert "coffre" not in out
    assert "code" not in out
    assert "FR" in out


def test_maybe_redact_passthrough():
    assert maybe_redact("Hello", "en", False) == "Hello"
    assert maybe_redact("Hello", "en", True) == "[EN 5 chars / 1 words]"
    # None + redact_enabled=False renvoie string vide
    assert maybe_redact(None, "en", False) == ""


# ---------------------------------------------------------------------------
# Network lockdown
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _unlock_after_test():
    yield
    _reset_for_tests()


def test_lockdown_not_active_initially():
    assert is_locked_down() is False


def test_lockdown_blocks_public_address():
    lockdown_egress()
    assert is_locked_down() is True
    s = socket.socket()
    with pytest.raises(NetworkLockdownError):
        s.connect(("8.8.8.8", 53))
    s.close()


def test_lockdown_blocks_dns_name():
    lockdown_egress()
    s = socket.socket()
    with pytest.raises(NetworkLockdownError):
        s.connect(("huggingface.co", 443))
    s.close()


def test_lockdown_allows_loopback_ipv4():
    """127.0.0.1 doit rester autorisé (debugger, MCP, etc.)."""
    lockdown_egress()
    # On lance un serveur local, on s'y connecte, on vérifie que c'est OK.
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    client = socket.socket()
    client.connect(("127.0.0.1", port))
    client.close()
    server.close()


def test_lockdown_is_idempotent():
    lockdown_egress()
    lockdown_egress()  # ne doit pas exploser
    assert is_locked_down() is True


def test_create_connection_also_blocked():
    lockdown_egress()
    with pytest.raises(NetworkLockdownError):
        socket.create_connection(("1.1.1.1", 53), timeout=0.5)


# ---------------------------------------------------------------------------
# Manifest / hashes
# ---------------------------------------------------------------------------


def test_sha256_file(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"izvox")
    expected = hashlib.sha256(b"izvox").hexdigest()
    assert sha256_file(f) == expected


def test_verify_artifact_ok(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    verify_artifact(f, expected, delete_on_mismatch=False)
    assert f.exists()


def test_verify_artifact_mismatch_deletes(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"bad content")
    with pytest.raises(ManifestMismatchError):
        verify_artifact(f, "0" * 64, delete_on_mismatch=True)
    assert not f.exists()


def test_load_manifest_real_file():
    """Le manifest fourni dans le repo doit être valide et non vide."""
    manifest = load_manifest(Path("models/manifest.json"))
    assert "piper/fr_FR-upmc-medium/fr_FR-upmc-medium.onnx" in manifest
    record = manifest["piper/fr_FR-upmc-medium/fr_FR-upmc-medium.onnx"]
    assert len(record.sha256) == 64
    assert record.source and "huggingface.co" in record.source


def test_load_manifest_missing_file_returns_empty(tmp_path):
    manifest = load_manifest(tmp_path / "absent.json")
    assert manifest == {}


def test_load_manifest_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json")
    from src.security import ManifestError  # local pour éviter le top-level import
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_verify_unknown_artifact_strict_mode(tmp_path):
    """En mode strict, un artefact non listé doit lever."""
    p = tmp_path / "unknown.bin"
    p.write_bytes(b"abc")
    with pytest.raises(UnknownArtifactError):
        verify_artifact_from_manifest(p, "unknown.bin", {}, strict=True)


def test_verify_unknown_artifact_non_strict_warns(tmp_path):
    """Hors mode strict, un artefact non listé est laissé passer."""
    p = tmp_path / "unknown.bin"
    p.write_bytes(b"abc")
    verify_artifact_from_manifest(p, "unknown.bin", {}, strict=False)
    assert p.exists()


def test_verify_manifest_entry_matches(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"izvox")
    expected = hashlib.sha256(b"izvox").hexdigest()
    manifest_data = {
        "version": 1,
        "artifacts": {
            "x.bin": {"sha256": expected, "size": 5},
        },
    }
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps(manifest_data))
    loaded = load_manifest(mp)
    verify_artifact_from_manifest(p, "x.bin", loaded, strict=True)
    assert p.exists()


def test_verify_manifest_entry_mismatch_deletes(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"tampered")
    fake_expected = hashlib.sha256(b"the original").hexdigest()
    manifest_data = {
        "version": 1,
        "artifacts": {
            "x.bin": {"sha256": fake_expected, "size": 12},
        },
    }
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps(manifest_data))
    loaded = load_manifest(mp)
    with pytest.raises(ManifestMismatchError):
        verify_artifact_from_manifest(p, "x.bin", loaded, strict=False)
    assert not p.exists()
