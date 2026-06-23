"""
Package principal du traducteur bidirectionnel temps réel.

izvox est une solution clé en main de traduction bidirectionnelle
ultra-basse latence pour visioconférences (Teams, Zoom, Meet) sur Windows.
"""

__version__ = "2.0.0"
__author__ = "Expert Python AI"
__license__ = "MIT"

from .config import AppConfig, AudioConfig, STTConfig, TranslationConfig, TTSConfig, VADConfig
from .config import HardwareLevel, FlowDirection
from .exceptions import (
    TranslatorError,
    HardwareError,
    ModelError,
    ModelNotFoundError,
    ModelLoadError,
    AudioError,
    AudioDeviceNotFoundError,
    AudioStreamError,
    PipelineError,
    ConfigurationError,
)

__all__ = [
    "__version__",
    "AppConfig",
    "AudioConfig",
    "STTConfig",
    "TranslationConfig",
    "TTSConfig",
    "VADConfig",
    "HardwareLevel",
    "FlowDirection",
    "TranslatorError",
    "HardwareError",
    "ModelError",
    "ModelNotFoundError",
    "ModelLoadError",
    "AudioError",
    "AudioDeviceNotFoundError",
    "AudioStreamError",
    "PipelineError",
    "ConfigurationError",
]
