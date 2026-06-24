"""Tests pour les utilitaires (resample_pcm, format helpers)."""

import numpy as np
import pytest

from src.utils import format_duration, format_size, resample_pcm


def test_resample_identity():
    """src_rate == dst_rate doit retourner exactement les mêmes bytes."""
    audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16).tobytes()
    assert resample_pcm(audio, 16000, 16000) == audio


def test_resample_empty():
    assert resample_pcm(b"", 22050, 16000) == b""


def test_resample_downsample_duration_preserved():
    """22050 -> 16000 : la durée doit être préservée à ±2 samples."""
    duration_s = 1.0
    src_rate = 22050
    dst_rate = 16000
    samples = int(duration_s * src_rate)
    audio = np.sin(np.linspace(0, 2 * np.pi * 440, samples)) * 10000
    audio_bytes = audio.astype(np.int16).tobytes()

    out = resample_pcm(audio_bytes, src_rate, dst_rate)
    out_samples = len(out) // 2  # int16 = 2 bytes
    expected_samples = int(duration_s * dst_rate)
    assert abs(out_samples - expected_samples) <= 2


def test_resample_upsample_duration_preserved():
    """16000 -> 22050 (autre sens)."""
    duration_s = 0.5
    src_rate = 16000
    dst_rate = 22050
    samples = int(duration_s * src_rate)
    audio = np.random.randint(-5000, 5000, samples, dtype=np.int16).tobytes()

    out = resample_pcm(audio, src_rate, dst_rate)
    out_samples = len(out) // 2
    expected_samples = int(duration_s * dst_rate)
    assert abs(out_samples - expected_samples) <= 2


def test_resample_returns_int16():
    """La sortie doit rester int16 valide."""
    audio = np.random.randint(-1000, 1000, 8000, dtype=np.int16).tobytes()
    out = resample_pcm(audio, 22050, 16000)
    assert len(out) % 2 == 0
    arr = np.frombuffer(out, dtype=np.int16)
    assert arr.dtype == np.int16
    assert arr.min() >= -32768 and arr.max() <= 32767


def test_resample_roundtrip_keeps_energy_order():
    """Round-trip 16k -> 22050 -> 16k : énergie globalement préservée."""
    samples = 16000
    audio = (np.random.randn(samples) * 5000).astype(np.int16)
    audio_bytes = audio.tobytes()

    up = resample_pcm(audio_bytes, 16000, 22050)
    back = resample_pcm(up, 22050, 16000)
    arr = np.frombuffer(back, dtype=np.int16).astype(np.float64)

    original_rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    roundtrip_rms = float(np.sqrt(np.mean(arr ** 2)))
    # ±25 % de l'énergie d'origine (rééchantillonnage + clipping)
    assert 0.75 * original_rms <= roundtrip_rms <= 1.25 * original_rms


def test_format_duration():
    assert format_duration(0.5) == "500ms"
    assert format_duration(1.234) == "1.2s"
    assert format_duration(65) == "1m 5s"


def test_format_size():
    assert format_size(0) == "0.0 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"
