"""Tests pour src/security/memory.py — SecureAudioBuffer, scrub, mlock."""

import numpy as np
import pytest

from src.security.memory import (
    SecureAudioBuffer,
    is_memory_locked,
    lock_process_memory,
    secure_zero_array,
    secure_zero_bytearray,
)


# ---------------------------------------------------------------------------
# secure_zero_*
# ---------------------------------------------------------------------------


def test_secure_zero_array_int16():
    arr = np.array([1, 2, 3, -4, 5], dtype=np.int16)
    secure_zero_array(arr)
    assert (arr == 0).all()


def test_secure_zero_array_float32():
    arr = np.random.randn(100).astype(np.float32)
    secure_zero_array(arr)
    assert (arr == 0.0).all()


def test_secure_zero_array_empty():
    secure_zero_array(np.array([], dtype=np.int16))  # no crash


def test_secure_zero_array_none():
    secure_zero_array(None)  # noqa: F841 - tolère None


def test_secure_zero_bytearray():
    ba = bytearray(b"\x01\x02\x03secret")
    secure_zero_bytearray(ba)
    assert all(b == 0 for b in ba)
    assert len(ba) == 9


def test_secure_zero_array_view():
    """Une vue partagée doit aussi être écrasée."""
    base = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    view = base[1:4]
    secure_zero_array(view)
    assert (base == np.array([1, 0, 0, 0, 5], dtype=np.int16)).all()


# ---------------------------------------------------------------------------
# SecureAudioBuffer
# ---------------------------------------------------------------------------


def test_secure_audio_buffer_basic_ops():
    buf = SecureAudioBuffer()
    assert len(buf) == 0
    assert not buf

    chunk1 = np.ones(100, dtype=np.int16) * 10
    chunk2 = np.ones(200, dtype=np.int16) * 20
    buf.append(chunk1)
    buf.append(chunk2)
    assert len(buf) == 2
    assert bool(buf) is True

    out = buf.concat()
    assert out is not None
    assert out.size == 300
    assert out[0] == 10 and out[-1] == 20


def test_secure_audio_buffer_iter():
    buf = SecureAudioBuffer()
    a = np.array([1], dtype=np.int16)
    b = np.array([2], dtype=np.int16)
    buf.append(a)
    buf.append(b)
    chunks = list(buf)
    assert len(chunks) == 2


def test_secure_audio_buffer_secure_clear_overwrites():
    """Après secure_clear, les arrays sources sont remis à zéro."""
    buf = SecureAudioBuffer()
    chunk = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    buf.append(chunk)
    buf.secure_clear()
    # Le chunk original a été écrasé en place (référence partagée)
    assert (chunk == 0).all()
    assert len(buf) == 0


def test_secure_audio_buffer_concat_empty():
    buf = SecureAudioBuffer()
    assert buf.concat() is None


# ---------------------------------------------------------------------------
# lock_process_memory (best-effort)
# ---------------------------------------------------------------------------


def test_lock_process_memory_returns_bool():
    """lock_process_memory ne doit jamais crasher, même sans privilège."""
    result = lock_process_memory()
    assert isinstance(result, bool)
    # is_memory_locked doit refléter le retour
    if result:
        assert is_memory_locked() is True


def test_lock_process_memory_idempotent():
    lock_process_memory()
    r1 = is_memory_locked()
    lock_process_memory()
    r2 = is_memory_locked()
    assert r1 == r2
