"""Tests d'intégration légers (ne nécessitent pas de matériel audio)."""

from src.config import AppConfig, HardwareLevel


def test_full_config_lifecycle(tmp_path):
    """Vérifie qu'on peut créer, sauvegarder, recharger et muter la config."""
    config = AppConfig()
    config.apply_profile("balanced")
    yaml_path = tmp_path / "test.yaml"
    config.to_yaml(str(yaml_path))

    loaded = AppConfig.from_yaml(str(yaml_path))
    assert loaded.profile == "balanced"
    assert loaded.hardware_level == HardwareLevel.MEDIUM
    assert loaded.audio.sample_rate == 16000


def test_hardware_detection_runs():
    """Vérifie que la détection ne lève pas."""
    from src.hardware_detector import HardwareDetector
    info = HardwareDetector().detect()
    assert info is not None
    assert info.cpu_cores > 0
