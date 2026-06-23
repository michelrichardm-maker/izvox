"""
Fixtures pytest pour izvox.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Permet d'importer src/ depuis tests/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import AppConfig, AudioConfig, STTConfig  # noqa: E402


@pytest.fixture
def app_config() -> AppConfig:
    """Configuration légère pour les tests."""
    config = AppConfig()
    config.stt.model_size = "tiny"
    config.stt.device = "cpu"
    config.stt.compute_type = "int8"
    config.translation.model_name = "Helsinki-NLP/opus-mt-fr-en"
    config.translation.device = "cpu"
    config.vad.backend = "rms"
    return config


@pytest.fixture
def audio_config() -> AudioConfig:
    """Configuration audio par défaut."""
    return AudioConfig(sample_rate=16000, channels=1, chunk_size=1024)


@pytest.fixture
def stt_config() -> STTConfig:
    """Configuration STT légère."""
    return STTConfig(
        model_size="tiny",
        device="cpu",
        compute_type="int8",
        language="fr",
        beam_size=1,
        vad_filter=False,
    )


@pytest.fixture
def sample_audio_silence() -> bytes:
    """Audio silencieux (1s à 16 kHz)."""
    samples = 16000
    return np.zeros(samples, dtype=np.int16).tobytes()


@pytest.fixture
def sample_audio_loud() -> bytes:
    """Audio fort/aléatoire (1s à 16 kHz)."""
    samples = 16000
    audio = np.random.randint(-10000, 10000, samples, dtype=np.int16)
    return audio.tobytes()
