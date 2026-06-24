"""Tests pour src/security/integrity.py — manifest des sources."""

import pytest

from src.security.integrity import (
    compute_source_hashes,
    load_source_manifest,
    verify_source_integrity,
    write_source_manifest,
)


def _make_fake_project(root, files: dict[str, str]) -> None:
    """Crée une arborescence de test : files = {relpath: contenu}."""
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def test_compute_source_hashes_basic(tmp_path):
    _make_fake_project(tmp_path, {
        "src/foo.py": "print('hi')\n",
        "config/x.yaml": "k: v\n",
        "README.md": "izvox",
    })
    hashes = compute_source_hashes(tmp_path)
    assert "src/foo.py" in hashes
    assert "config/x.yaml" in hashes
    assert "README.md" in hashes
    for h in hashes.values():
        assert len(h) == 64


def test_skips_non_source_extensions(tmp_path):
    _make_fake_project(tmp_path, {
        "src/foo.py": "ok",
        "src/foo.pyc": "binary",
        "src/data.bin": "binary",
        "models/big.onnx": "model",
    })
    hashes = compute_source_hashes(tmp_path)
    assert "src/foo.py" in hashes
    assert "src/foo.pyc" not in hashes
    assert "src/data.bin" not in hashes
    # `models/` n'est pas dans SOURCE_DIRS
    assert "models/big.onnx" not in hashes


def test_skips_cache_dirs(tmp_path):
    _make_fake_project(tmp_path, {
        "src/__pycache__/cached.py": "cached",
        "src/real.py": "real",
        ".pytest_cache/v/something.py": "ignore",
    })
    hashes = compute_source_hashes(tmp_path)
    assert "src/real.py" in hashes
    assert all("__pycache__" not in k for k in hashes)
    assert all(".pytest_cache" not in k for k in hashes)


def test_write_and_load_manifest_roundtrip(tmp_path):
    _make_fake_project(tmp_path, {
        "src/a.py": "a",
        "src/b.py": "b",
    })
    hashes = compute_source_hashes(tmp_path)
    mpath = tmp_path / "SOURCES.sha256"
    write_source_manifest(mpath, hashes)
    loaded = load_source_manifest(mpath)
    assert loaded == hashes


def test_verify_ok_on_unchanged(tmp_path):
    _make_fake_project(tmp_path, {
        "src/a.py": "stable",
    })
    write_source_manifest(
        tmp_path / "SOURCES.sha256",
        compute_source_hashes(tmp_path),
    )
    result = verify_source_integrity(tmp_path, tmp_path / "SOURCES.sha256")
    assert result.ok is True
    assert result.total == 1
    assert result.mismatched == []


def test_verify_detects_modified(tmp_path):
    _make_fake_project(tmp_path, {"src/a.py": "original"})
    write_source_manifest(
        tmp_path / "SOURCES.sha256",
        compute_source_hashes(tmp_path),
    )

    (tmp_path / "src" / "a.py").write_text("MODIFIED", encoding="utf-8")
    result = verify_source_integrity(tmp_path, tmp_path / "SOURCES.sha256")
    assert result.ok is False
    assert "src/a.py" in result.mismatched


def test_verify_detects_missing(tmp_path):
    _make_fake_project(tmp_path, {
        "src/a.py": "stable",
        "src/b.py": "to be deleted",
    })
    write_source_manifest(
        tmp_path / "SOURCES.sha256",
        compute_source_hashes(tmp_path),
    )
    (tmp_path / "src" / "b.py").unlink()
    result = verify_source_integrity(tmp_path, tmp_path / "SOURCES.sha256")
    assert result.ok is False
    assert "src/b.py" in result.missing


def test_verify_extra_allowed_by_default(tmp_path):
    _make_fake_project(tmp_path, {"src/a.py": "ok"})
    write_source_manifest(
        tmp_path / "SOURCES.sha256",
        compute_source_hashes(tmp_path),
    )
    (tmp_path / "src" / "b.py").write_text("added later", encoding="utf-8")
    result = verify_source_integrity(
        tmp_path, tmp_path / "SOURCES.sha256", allow_extra=True
    )
    assert result.ok is True
    assert "src/b.py" in result.extra


def test_verify_extra_rejected_in_strict(tmp_path):
    _make_fake_project(tmp_path, {"src/a.py": "ok"})
    write_source_manifest(
        tmp_path / "SOURCES.sha256",
        compute_source_hashes(tmp_path),
    )
    (tmp_path / "src" / "b.py").write_text("smuggled", encoding="utf-8")
    result = verify_source_integrity(
        tmp_path, tmp_path / "SOURCES.sha256", allow_extra=False
    )
    assert result.ok is False
    assert "src/b.py" in result.extra
