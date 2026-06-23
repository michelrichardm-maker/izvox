"""
Gestionnaire de modèles AI.

Télécharge, cache et charge les modèles selon le profil détecté.
Sélectionne automatiquement les meilleurs modèles en fonction du matériel.
"""

import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AppConfig, HardwareLevel
from .exceptions import ModelDownloadError
from .hardware_detector import HardwareDetector, HardwareInfo


@dataclass
class ModelPaths:
    """Chemins vers les modèles chargés."""
    whisper: Optional[str] = None
    nllb: Optional[str] = None
    piper_fr: Optional[Path] = None
    piper_en: Optional[Path] = None
    silero_vad: Optional[Any] = None


class ModelManager:
    """
    Gère le téléchargement et la configuration des modèles AI.

    Usage:
        manager = ModelManager(config)
        manager.initialize()
        models = manager.get_models()
    """

    PROFILES = {
        HardwareLevel.HIGH: {
            "stt_model": "large-v3",
            "stt_compute_type": "float16",
            "translation_model": "facebook/nllb-200-3.3B",
            "tts_quality": "high",
            "vad_backend": "silero",
        },
        HardwareLevel.MEDIUM: {
            "stt_model": "medium",
            "stt_compute_type": "int8",
            "translation_model": "facebook/nllb-200-1.3B",
            "tts_quality": "medium",
            "vad_backend": "silero",
        },
        HardwareLevel.LOW: {
            "stt_model": "small",
            "stt_compute_type": "int8",
            "translation_model": "facebook/nllb-200-distilled-600M",
            "tts_quality": "low",
            "vad_backend": "silero",
        },
        HardwareLevel.CPU_ONLY: {
            "stt_model": "tiny",
            "stt_compute_type": "int8",
            "translation_model": "Helsinki-NLP/opus-mt-fr-en",
            "tts_quality": "low",
            "vad_backend": "rms",
        },
    }

    PIPER_VOICES = {
        "fr_FR-upmc-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/",
            "files": ["fr_FR-upmc-medium.onnx", "fr_FR-upmc-medium.onnx.json"],
        },
        "en_US-lessac-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/",
            "files": ["en_US-lessac-medium.onnx", "en_US-lessac-medium.onnx.json"],
        },
        "fr_FR-siwis-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/",
            "files": ["fr_FR-siwis-medium.onnx", "fr_FR-siwis-medium.onnx.json"],
        },
        "en_US-amy-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/",
            "files": ["en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"],
        },
    }

    def __init__(self, config: AppConfig, auto_detect: bool = True):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.models_dir = Path(config.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.hardware_info: Optional[HardwareInfo] = None
        self.profile: Optional[Dict[str, str]] = None
        self.model_paths = ModelPaths()

        if auto_detect:
            self._detect_and_configure()

    def _detect_and_configure(self) -> None:
        detector = HardwareDetector()
        self.hardware_info = detector.detect()
        self.profile = self.PROFILES[self.hardware_info.level]
        self._apply_profile_to_config()

    def _apply_profile_to_config(self) -> None:
        if not self.profile or not self.hardware_info:
            return

        self.config.hardware_level = self.hardware_info.level
        self.config.stt.model_size = self.profile["stt_model"]
        self.config.stt.compute_type = self.profile["stt_compute_type"]
        self.config.stt.device = self.hardware_info.recommended_device

        self.config.translation.model_name = self.profile["translation_model"]
        self.config.translation.device = self.hardware_info.recommended_device

        self.config.vad.backend = self.profile["vad_backend"]

    def initialize(self, verbose: bool = True) -> Dict[str, Any]:
        """Vérifie/télécharge les modèles et configure le contexte."""
        if verbose and self.hardware_info:
            HardwareDetector().print_info(self.hardware_info)
            self._print_profile()

        self._setup_whisper()
        self._setup_translation()
        self._setup_piper()
        self._setup_vad()

        return {
            "hardware": self.hardware_info,
            "profile": self.profile,
            "models": self.model_paths,
        }

    def _print_profile(self) -> None:
        if not self.profile or not self.hardware_info:
            return
        print(f"\n📊 PROFIL: {self.hardware_info.level.value.upper()}")
        print("=" * 70)
        print(
            f"STT: Whisper {self.profile['stt_model']} "
            f"({self.profile['stt_compute_type']})"
        )
        print(f"Traduction: {self.profile['translation_model']}")
        print(f"TTS: Piper {self.profile['tts_quality']}")
        print(f"VAD: {self.profile['vad_backend']}")
        print("=" * 70)

    def _setup_whisper(self) -> None:
        self.logger.info(f"Configuration Whisper: {self.config.stt.model_size}")
        Path(self.config.stt.download_root).mkdir(parents=True, exist_ok=True)
        self.model_paths.whisper = self.config.stt.model_size

    def _setup_translation(self) -> None:
        self.logger.info(
            f"Configuration traduction: {self.config.translation.model_name}"
        )
        Path(self.config.translation.cache_dir).mkdir(parents=True, exist_ok=True)
        self.model_paths.nllb = self.config.translation.model_name

    def _setup_piper(self) -> None:
        piper_dir = self.models_dir / "piper"
        piper_dir.mkdir(exist_ok=True)

        for voice_name in (self.config.tts.voice_fr, self.config.tts.voice_en):
            voice_dir = piper_dir / voice_name
            if not self._check_piper_voice(voice_dir, voice_name):
                self._download_piper_voice(voice_name, voice_dir)

        self.model_paths.piper_fr = piper_dir / self.config.tts.voice_fr
        self.model_paths.piper_en = piper_dir / self.config.tts.voice_en

    def _check_piper_voice(self, voice_dir: Path, voice_name: str) -> bool:
        if voice_name not in self.PIPER_VOICES:
            return False
        for filename in self.PIPER_VOICES[voice_name]["files"]:
            if not (voice_dir / filename).exists():
                return False
        return True

    def _download_piper_voice(self, voice_name: str, voice_dir: Path) -> None:
        if voice_name not in self.PIPER_VOICES:
            self.logger.warning(f"Voix inconnue: {voice_name}")
            return

        voice_info = self.PIPER_VOICES[voice_name]
        voice_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Téléchargement voix Piper: {voice_name}")

        for filename in voice_info["files"]:
            url = voice_info["url"] + filename
            filepath = voice_dir / filename
            if filepath.exists():
                continue
            self.logger.info(f"  Téléchargement: {filename}")
            try:
                urllib.request.urlretrieve(url, filepath)
            except Exception as e:  # noqa: BLE001
                if filepath.exists():
                    filepath.unlink()
                raise ModelDownloadError(
                    f"Échec téléchargement {filename}: {e}"
                ) from e

    def _setup_vad(self) -> None:
        if self.config.vad.backend == "silero":
            self.logger.info("Configuration Silero VAD")
        else:
            self.logger.info("Configuration VAD RMS (simple)")

    def get_config(self) -> AppConfig:
        return self.config

    def get_models(self) -> ModelPaths:
        return self.model_paths

    def get_recommended_audio_config(self) -> Dict[str, Any]:
        chunk_sizes = {
            HardwareLevel.HIGH: 1024,
            HardwareLevel.MEDIUM: 1024,
            HardwareLevel.LOW: 2048,
            HardwareLevel.CPU_ONLY: 2048,
        }
        level = (
            self.hardware_info.level if self.hardware_info else HardwareLevel.CPU_ONLY
        )
        return {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": chunk_sizes[level],
            "format": "int16",
        }
