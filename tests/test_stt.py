"""Tests pour le STT.

Marqués `slow` car le téléchargement de Whisper tiny prend ~75 MB.
"""

import pytest

from src.config import STTConfig

try:
    from src.stt import STTProcessor
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


pytestmark = pytest.mark.skipif(
    not HAS_DEPS, reason="faster-whisper non installé"
)


def test_stt_buffer_empty():
    """Test pour vérifier que le buffer vide ne déclenche pas de transcription."""
    config = STTConfig(
        model_size="tiny", device="cpu", compute_type="int8",
        beam_size=1, vad_filter=False,
    )
    try:
        stt = STTProcessor(config)
    except Exception as e:
        pytest.skip(f"Modèle Whisper indisponible: {e}")

    assert stt.transcribe(flush=False) is None
    assert stt.transcribe(flush=True) is None


def test_stt_buffer_clear():
    config = STTConfig(
        model_size="tiny", device="cpu", compute_type="int8",
        beam_size=1, vad_filter=False,
    )
    try:
        stt = STTProcessor(config)
    except Exception as e:
        pytest.skip(f"Modèle Whisper indisponible: {e}")

    silence = b"\x00\x00" * 16000  # 1s à 16kHz
    stt.add_audio(silence, 16000)
    assert stt.buffer_duration == pytest.approx(1.0)

    stt.clear_buffer()
    assert stt.buffer_duration == 0
    assert stt.audio_buffer == []


def test_stt_default_min_duration():
    """Fix B3 : min_duration par défaut doit être 0.4s pour capter les
    phrases courtes."""
    config = STTConfig(
        model_size="tiny", device="cpu", compute_type="int8",
        beam_size=1, vad_filter=False,
    )
    try:
        stt = STTProcessor(config)
    except Exception as e:
        pytest.skip(f"Modèle Whisper indisponible: {e}")
    assert stt.min_duration == 0.4
    assert stt.external_vad is True


def test_stt_external_vad_flag():
    """external_vad=False doit garder le VAD interne actif."""
    config = STTConfig(
        model_size="tiny", device="cpu", compute_type="int8",
        beam_size=1, vad_filter=False,
    )
    try:
        stt = STTProcessor(config, external_vad=False)
    except Exception as e:
        pytest.skip(f"Modèle Whisper indisponible: {e}")
    assert stt.external_vad is False
