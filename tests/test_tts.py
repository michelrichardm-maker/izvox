"""Tests pour le TTS (gracieusement skip si Piper indisponible)."""

from pathlib import Path

import pytest

from src.config import TTSConfig
from src.tts import TTSProcessor

# Voix Piper FR utilisée pour les tests réels en CI
PIPER_FR_VOICE = "fr_FR-upmc-medium"
PIPER_FR_ONNX = Path("./models/piper") / PIPER_FR_VOICE / f"{PIPER_FR_VOICE}.onnx"


def _piper_fr_available() -> bool:
    """La voix Piper FR est-elle téléchargée ET la lib piper-tts présente ?"""
    if not PIPER_FR_ONNX.exists():
        return False
    try:
        import piper  # type: ignore  # noqa: F401
    except ImportError:
        return False
    return True


def test_tts_handles_missing_piper(tmp_path):
    """Si Piper n'est pas installé OU si la voix n'est pas téléchargée,
    TTSProcessor doit dégrader gracieusement (voice=None)."""
    config = TTSConfig(model_path=str(tmp_path / "piper"))
    tts = TTSProcessor(config, language="en")
    # Soit Piper n'est pas installé, soit la voix n'est pas téléchargée.
    # Dans les deux cas, voice doit être None.
    assert tts.voice is None


def test_tts_synthesize_returns_none_on_empty(tmp_path):
    config = TTSConfig(model_path=str(tmp_path / "piper"))
    tts = TTSProcessor(config, language="en")
    assert tts.synthesize("") is None
    assert tts.synthesize("   ") is None


def test_tts_synthesize_returns_none_without_voice(tmp_path):
    config = TTSConfig(model_path=str(tmp_path / "piper"))
    tts = TTSProcessor(config, language="en")
    assert tts.synthesize("Hello") is None


def test_tts_set_language(tmp_path):
    config = TTSConfig(model_path=str(tmp_path / "piper"))
    tts = TTSProcessor(config, language="en")
    tts.set_language("fr")
    assert tts.language == "fr"


@pytest.mark.skipif(
    not _piper_fr_available(),
    reason="Piper FR voice not downloaded (run download_models.py or rely on CI)",
)
def test_tts_real_synthesis_with_piper():
    """Si la voix Piper FR est dispo, on exerce le vrai chemin de synthèse
    et on vérifie qu'on obtient bien du PCM int16 non-vide."""
    config = TTSConfig(model_path="./models/piper")
    tts = TTSProcessor(config, language="fr")
    assert tts.voice is not None, "TTSProcessor n'a pas chargé la voix FR"

    audio = tts.synthesize("Bonjour, ceci est un test.")
    assert audio is not None
    assert isinstance(audio, (bytes, bytearray))
    # Au moins ~0.2s d'audio à 22050 Hz int16 = 8820 bytes
    assert len(audio) >= 4000, f"Audio trop court: {len(audio)} bytes"
    # Longueur paire (int16 = 2 bytes par sample)
    assert len(audio) % 2 == 0
