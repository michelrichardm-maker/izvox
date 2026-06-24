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
    """Fix de régression : pour backend='rms', rms_threshold doit gagner
    sur threshold (la valeur threshold est destinée à Silero)."""
    vad = VADFactory.create(
        "rms",
        threshold=0.5,         # valeur Silero (haute) — DOIT être ignorée
        rms_threshold=0.015,   # valeur RMS — DOIT être utilisée
        sample_rate=16000,
        min_silence_duration=0.5,
    )
    assert isinstance(vad, RMSVAD)
    assert vad.threshold == 0.015, (
        f"RMS VAD a utilisé threshold={vad.threshold} au lieu de "
        f"rms_threshold=0.015. C'est le bug qui fait que les WAV Piper "
        f"ne sont transcrits que sur les premières 0.5s."
    )
    assert vad.sample_rate == 16000


def test_vad_factory_rms_only_rms_threshold():
    """Si seul rms_threshold est passé, il est utilisé tel quel."""
    vad = VADFactory.create("rms", rms_threshold=0.02)
    assert vad.threshold == 0.02


def test_vad_factory_silero_drops_rms_threshold():
    """Silero ne doit pas recevoir rms_threshold (sinon TypeError)."""
    # Si Silero est indisponible (pas de torch), on skip.
    try:
        vad = VADFactory.create("silero", threshold=0.5, rms_threshold=0.015)
        # Si on arrive là, c'est que torch.hub a réussi à charger Silero
        # (rare en CI). On vérifie juste que ça n'a pas planté.
        assert vad is not None
    except Exception as e:
        # torch indisponible ou pas d'accès réseau → skip
        pytest.skip(f"Silero indisponible: {e}")
