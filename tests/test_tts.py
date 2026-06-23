"""Tests pour le TTS (gracieusement skip si Piper indisponible)."""

import pytest

from src.config import TTSConfig
from src.tts import TTSProcessor


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
