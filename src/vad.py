"""
Voice Activity Detection (VAD).

Détecte quand l'utilisateur parle pour éviter les traductions de silence.
Deux backends disponibles:
  - Silero VAD (neural, haute précision)
  - RMS VAD (énergie, ultra-léger, fallback CPU)
"""

import logging
from abc import ABC, abstractmethod

import numpy as np


class BaseVAD(ABC):
    """Interface de base pour les détecteurs d'activité vocale."""

    @abstractmethod
    def is_speech(self, audio_chunk: bytes) -> bool:
        """Retourne True si le chunk audio contient de la parole."""

    @abstractmethod
    def reset(self) -> None:
        """Réinitialise l'état du VAD."""


class SileroVAD(BaseVAD):
    """
    VAD basé sur Silero (modèle neural haute précision).
    """

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000,
                 min_silence_duration: float = 0.5, **kwargs):
        del kwargs
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.min_silence_duration = min_silence_duration
        self.logger = logging.getLogger(__name__)

        self.silence_samples = 0
        self.max_silence_samples = int(min_silence_duration * sample_rate)

        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            import torch  # type: ignore

            self.model, _utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            self.model.eval()
            self.logger.info("✓ Silero VAD chargé")
        except Exception as e:
            self.logger.error(f"Erreur chargement Silero VAD: {e}")
            raise

    def is_speech(self, audio_chunk: bytes) -> bool:
        try:
            import torch  # type: ignore

            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float)

            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.sample_rate).item()

            if speech_prob > self.threshold:
                self.silence_samples = 0
                return True
            self.silence_samples += len(audio_array)
            return self.silence_samples < self.max_silence_samples
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Erreur VAD: {e}")
            return True

    def reset(self) -> None:
        self.silence_samples = 0


class RMSVAD(BaseVAD):
    """
    VAD simple basé sur l'énergie RMS.
    Plus léger que Silero, adapté aux CPU faibles.
    """

    def __init__(self, threshold: float = 0.015, sample_rate: int = 16000,
                 min_silence_duration: float = 0.5, **kwargs):
        del kwargs
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.min_silence_duration = min_silence_duration
        self.logger = logging.getLogger(__name__)

        self.silence_samples = 0
        self.max_silence_samples = int(min_silence_duration * sample_rate)

        self.logger.info(f"✓ RMS VAD initialisé (seuil: {threshold})")

    def is_speech(self, audio_chunk: bytes) -> bool:
        try:
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            if len(audio_array) == 0:
                return False
            rms = np.sqrt(
                np.mean(audio_array.astype(np.float32) ** 2)
            ) / 32768.0

            if rms > self.threshold:
                self.silence_samples = 0
                return True
            self.silence_samples += len(audio_array)
            return self.silence_samples < self.max_silence_samples
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Erreur RMS VAD: {e}")
            return True

    def reset(self) -> None:
        self.silence_samples = 0


class VADFactory:
    """Factory pour créer le bon type de VAD selon le backend."""

    @staticmethod
    def create(backend: str = "silero", **kwargs) -> BaseVAD:
        backend = backend.lower()
        if backend == "silero":
            return SileroVAD(**kwargs)
        if backend == "rms":
            # Accepte threshold ou rms_threshold
            if "rms_threshold" in kwargs and "threshold" not in kwargs:
                kwargs["threshold"] = kwargs.pop("rms_threshold")
            else:
                kwargs.pop("rms_threshold", None)
            return RMSVAD(**kwargs)
        raise ValueError(f"Backend VAD inconnu: {backend}")
