"""Tests pour le module de configuration."""

from pathlib import Path

import pytest

from src.config import AppConfig, AudioConfig, HardwareLevel
from src.exceptions import ConfigurationError


def test_appconfig_defaults():
    config = AppConfig()
    assert config.profile == "balanced"
    assert config.hardware_level == HardwareLevel.MEDIUM
    assert config.audio.sample_rate == 16000
    assert config.stt.model_size == "medium"


def test_apply_profile_high():
    config = AppConfig()
    config.apply_profile("high_performance")
    assert config.stt.model_size == "large-v3"
    assert config.translation.model_name == "facebook/nllb-200-3.3B"
    assert config.hardware_level == HardwareLevel.HIGH


def test_apply_profile_cpu():
    config = AppConfig()
    config.apply_profile("cpu_only")
    assert config.stt.model_size == "tiny"
    assert config.stt.device == "cpu"
    assert config.translation.model_name == "Helsinki-NLP/opus-mt-fr-en"
    assert config.vad.backend == "rms"
    assert config.hardware_level == HardwareLevel.CPU_ONLY


def test_apply_profile_unknown():
    config = AppConfig()
    with pytest.raises(ConfigurationError):
        config.apply_profile("nonexistent_profile")


def test_yaml_roundtrip(tmp_path: Path):
    config = AppConfig()
    config.apply_profile("low_resource")
    config.audio.chunk_size = 1234

    yaml_path = tmp_path / "config.yaml"
    config.to_yaml(str(yaml_path))
    assert yaml_path.exists()

    loaded = AppConfig.from_yaml(str(yaml_path))
    assert loaded.profile == "low_resource"
    assert loaded.audio.chunk_size == 1234
    assert loaded.stt.model_size == "small"
    assert loaded.translation.model_name == "facebook/nllb-200-distilled-600M"


def test_from_yaml_missing_file():
    with pytest.raises(ConfigurationError):
        AppConfig.from_yaml("/nonexistent/path/to/config.yaml")


def test_audio_config_defaults():
    cfg = AudioConfig()
    assert cfg.sample_rate == 16000
    assert cfg.channels == 1
    assert cfg.vbcable_input_pattern == "CABLE Input"
    assert cfg.vbcable_output_pattern == "CABLE-B"
