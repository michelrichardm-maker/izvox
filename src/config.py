"""
Configuration centralisée du traducteur izvox.

Gère les paramètres audio, modèles, et profils de performance.
La configuration peut être chargée depuis un fichier YAML ou créée
programmatiquement, puis ajustée selon le matériel détecté.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from .exceptions import ConfigurationError


class HardwareLevel(Enum):
    """Niveau de performance matérielle détecté."""
    HIGH = "high"           # RTX 3060+ (12GB+ VRAM)
    MEDIUM = "medium"       # RTX 2060, 3050 (6-8GB VRAM)
    LOW = "low"             # GPU intégré ou ancien
    CPU_ONLY = "cpu_only"   # Pas de GPU dédié


class FlowDirection(Enum):
    """Direction du flux de traduction."""
    OUTGOING = "outgoing"   # Utilisateur → Interlocuteur (FR→EN)
    INCOMING = "incoming"   # Interlocuteur → Utilisateur (EN→FR)


@dataclass
class AudioConfig:
    """Configuration audio."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: str = "int16"
    vad_threshold: float = 0.015
    silence_duration: float = 0.5

    input_device_pattern: str = ""
    output_device_pattern: str = ""
    vbcable_input_pattern: str = "CABLE Input"
    vbcable_output_pattern: str = "CABLE-B"


@dataclass
class STTConfig:
    """Configuration Speech-to-Text (Faster-Whisper)."""
    model_size: str = "medium"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "fr"
    beam_size: int = 5
    vad_filter: bool = True
    download_root: str = "./models/whisper"


@dataclass
class TranslationConfig:
    """Configuration Traduction (NLLB / Opus-MT)."""
    model_name: str = "facebook/nllb-200-1.3B"
    device: str = "cuda"
    source_lang: str = "fra_Latn"
    target_lang: str = "eng_Latn"
    max_length: int = 512
    num_beams: int = 5
    cache_dir: str = "./models/nllb"


@dataclass
class TTSConfig:
    """Configuration Text-to-Speech (Piper)."""
    model_path: str = "./models/piper"
    voice_fr: str = "fr_FR-upmc-medium"
    voice_en: str = "en_US-lessac-medium"
    sample_rate: int = 22050
    speaker_id: Optional[int] = None


@dataclass
class VADConfig:
    """Configuration Voice Activity Detection."""
    backend: str = "silero"
    threshold: float = 0.5
    rms_threshold: float = 0.015
    min_speech_duration: float = 0.1
    min_silence_duration: float = 0.5
    sample_rate: int = 16000


@dataclass
class AppConfig:
    """Configuration globale de l'application."""
    profile: str = "balanced"
    hardware_level: HardwareLevel = HardwareLevel.MEDIUM

    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    vad: VADConfig = field(default_factory=VADConfig)

    models_dir: Path = field(default_factory=lambda: Path("./models"))
    logs_dir: Path = field(default_factory=lambda: Path("./logs"))
    config_dir: Path = field(default_factory=lambda: Path("./config"))

    verbose: bool = False
    log_level: str = "INFO"
    enable_stats: bool = True

    # Zero-trust / confidentialité
    redact_logs: bool = True        # Masque le contenu textuel dans les logs
    in_memory_only: bool = False    # Refuse tout artefact disque (logs, fichiers WAV)
    network_lockdown: bool = False  # Bloque l'egress non-loopback après init
    strict_models: bool = False     # Refuse les modèles non listés dans manifest

    @classmethod
    def from_yaml(cls, filepath: str) -> "AppConfig":
        """Charge la configuration depuis un fichier YAML."""
        path = Path(filepath)
        if not path.exists():
            raise ConfigurationError(f"Fichier de configuration introuvable: {filepath}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML invalide dans {filepath}: {e}") from e

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Construit la config depuis un dictionnaire."""
        config = cls()

        if "profile" in data:
            config.profile = data["profile"]
        if "hardware_level" in data:
            try:
                config.hardware_level = HardwareLevel(data["hardware_level"])
            except ValueError as e:
                raise ConfigurationError(
                    f"hardware_level invalide: {data['hardware_level']}"
                ) from e

        section_specs = {
            "audio": (AudioConfig, "audio"),
            "stt": (STTConfig, "stt"),
            "translation": (TranslationConfig, "translation"),
            "tts": (TTSConfig, "tts"),
            "vad": (VADConfig, "vad"),
        }

        for key, (dataclass_type, attr_name) in section_specs.items():
            if key in data and isinstance(data[key], dict):
                current = getattr(config, attr_name)
                for field_name, field_value in data[key].items():
                    if hasattr(current, field_name):
                        setattr(current, field_name, field_value)

        for path_key in ("models_dir", "logs_dir", "config_dir"):
            if path_key in data:
                setattr(config, path_key, Path(data[path_key]))

        for opt in (
            "verbose", "log_level", "enable_stats",
            "redact_logs", "in_memory_only", "network_lockdown", "strict_models",
        ):
            if opt in data:
                setattr(config, opt, data[opt])

        return config

    def to_yaml(self, filepath: str) -> None:
        """Sauvegarde la configuration dans un fichier YAML."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "profile": self.profile,
            "hardware_level": self.hardware_level.value,
            "audio": asdict(self.audio),
            "stt": asdict(self.stt),
            "translation": asdict(self.translation),
            "tts": asdict(self.tts),
            "vad": asdict(self.vad),
            "models_dir": str(self.models_dir),
            "logs_dir": str(self.logs_dir),
            "config_dir": str(self.config_dir),
            "verbose": self.verbose,
            "log_level": self.log_level,
            "enable_stats": self.enable_stats,
            "redact_logs": self.redact_logs,
            "in_memory_only": self.in_memory_only,
            "network_lockdown": self.network_lockdown,
            "strict_models": self.strict_models,
        }

        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    def apply_profile(self, profile_name: str) -> None:
        """Applique un profil de performance prédéfini."""
        profiles = {
            "high_performance": self._profile_high,
            "balanced": self._profile_balanced,
            "low_resource": self._profile_low,
            "cpu_only": self._profile_cpu,
        }
        if profile_name not in profiles:
            raise ConfigurationError(f"Profil inconnu: {profile_name}")
        self.profile = profile_name
        profiles[profile_name]()

    def _profile_high(self) -> None:
        self.stt.model_size = "large-v3"
        self.stt.device = "cuda"
        self.stt.compute_type = "float16"
        self.translation.model_name = "facebook/nllb-200-3.3B"
        self.translation.device = "cuda"
        self.vad.backend = "silero"
        self.audio.chunk_size = 1024
        self.hardware_level = HardwareLevel.HIGH

    def _profile_balanced(self) -> None:
        self.stt.model_size = "medium"
        self.stt.device = "cuda"
        self.stt.compute_type = "int8"
        self.translation.model_name = "facebook/nllb-200-1.3B"
        self.translation.device = "cuda"
        self.vad.backend = "silero"
        self.audio.chunk_size = 1024
        self.hardware_level = HardwareLevel.MEDIUM

    def _profile_low(self) -> None:
        self.stt.model_size = "small"
        self.stt.device = "cuda"
        self.stt.compute_type = "int8"
        self.translation.model_name = "facebook/nllb-200-distilled-600M"
        self.translation.device = "cuda"
        self.vad.backend = "silero"
        self.audio.chunk_size = 2048
        self.hardware_level = HardwareLevel.LOW

    def _profile_cpu(self) -> None:
        self.stt.model_size = "tiny"
        self.stt.device = "cpu"
        self.stt.compute_type = "int8"
        self.translation.model_name = "Helsinki-NLP/opus-mt-fr-en"
        self.translation.device = "cpu"
        self.vad.backend = "rms"
        self.audio.chunk_size = 2048
        self.hardware_level = HardwareLevel.CPU_ONLY
