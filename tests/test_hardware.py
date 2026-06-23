"""Tests pour la détection matérielle."""

from src.config import HardwareLevel
from src.hardware_detector import HardwareDetector, HardwareInfo


def test_hardware_detection():
    detector = HardwareDetector()
    info = detector.detect()

    assert isinstance(info, HardwareInfo)
    assert info.cpu_cores > 0
    assert info.ram_gb >= 0
    assert info.level in HardwareLevel


def test_hardware_level_assignment():
    detector = HardwareDetector()
    info = detector.detect()

    # Cohérence du niveau avec les capacités détectées
    if info.has_cuda and info.vram_mb >= 12000:
        assert info.level == HardwareLevel.HIGH
    elif info.has_cuda and info.vram_mb >= 6000:
        assert info.level == HardwareLevel.MEDIUM
    elif info.has_cuda:
        assert info.level == HardwareLevel.LOW
    elif info.has_directml:
        assert info.level == HardwareLevel.MEDIUM
    else:
        assert info.level == HardwareLevel.CPU_ONLY
        assert info.recommended_device == "cpu"


def test_hardware_info_defaults():
    info = HardwareInfo()
    assert info.has_cuda is False
    assert info.has_directml is False
    assert info.level == HardwareLevel.CPU_ONLY
    assert info.recommended_device == "cpu"
