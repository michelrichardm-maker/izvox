"""Tests pour les VAD."""

import numpy as np
import pytest

from src.vad import RMSVAD, VADFactory


def test_rms_vad_silence(sample_audio_silence):
    vad = RMSVAD(threshold=0.1, min_silence_duration=0.05, sample_rate=16000)
    # Le VAD continue de retourner True pendant min_silence_duration
    # On fait suffisamment d'appels pour dépasser ce seuil
    result = None
    for _ in range(20):
        result = vad.is_speech(sample_audio_silence)
    assert result is False


def test_rms_vad_loud_signal(sample_audio_loud):
    vad = RMSVAD(threshold=0.01)
    assert vad.is_speech(sample_audio_loud) is True


def test_rms_vad_reset():
    vad = RMSVAD(threshold=0.001, min_silence_duration=0.05)
    silence = np.zeros(1600, dtype=np.int16).tobytes()
    for _ in range(20):
        vad.is_speech(silence)
    assert vad.silence_samples > 0
    vad.reset()
    assert vad.silence_samples == 0


def test_vad_factory_rms():
    vad = VADFactory.create("rms", threshold=0.02)
    assert isinstance(vad, RMSVAD)


def test_vad_factory_unknown():
    with pytest.raises(ValueError):
        VADFactory.create("nonexistent_backend")


def test_vad_factory_rms_with_kwargs():
    vad = VADFactory.create(
        "rms",
        threshold=0.02,
        rms_threshold=0.03,
        sample_rate=16000,
        min_silence_duration=0.5,
    )
    # threshold a priorité quand fourni explicitement
    assert isinstance(vad, RMSVAD)
    assert vad.sample_rate == 16000
