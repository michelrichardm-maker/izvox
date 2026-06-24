"""
Speech-to-Text avec Faster-Whisper.

Transcrit l'audio en texte avec haute précision et faible latence.
Le modèle est sélectionné automatiquement par ModelManager selon le matériel.
"""

import logging
from typing import Optional

import numpy as np

from .config import STTConfig
from .exceptions import ModelLoadError
from .security.memory import SecureAudioBuffer


class STTProcessor:
    """
    Processeur Speech-to-Text basé sur Faster-Whisper.

    Usage:
        stt = STTProcessor(config)
        stt.add_audio(audio_chunk)
        text = stt.transcribe()
    """

    def __init__(self, config: STTConfig, min_duration: float = 0.4,
                 external_vad: bool = True):
        """
        Args:
            config: configuration STT
            min_duration: durée minimale (s) avant de tenter une transcription.
                0.4 par défaut pour capter les phrases courtes (« OK »,
                « D'accord »).
            external_vad: True si un VAD upstream filtre déjà l'audio
                (cas du pipeline). Dans ce cas on désactive le VAD interne
                de Whisper pour éviter un double filtrage qui clippe les
                débuts/fins de phrase.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.external_vad = external_vad

        self.audio_buffer = SecureAudioBuffer()
        self.buffer_duration: float = 0.0
        self.min_duration: float = min_duration

        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        self.logger.info(
            f"Chargement Whisper {self.config.model_size} "
            f"sur {self.config.device}..."
        )
        try:
            from faster_whisper import WhisperModel  # type: ignore

            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                download_root=self.config.download_root,
            )
            self.logger.info(f"✓ Whisper {self.config.model_size} chargé")
        except ImportError as e:
            raise ModelLoadError(
                "faster-whisper non installé. "
                "Installez-le avec: pip install faster-whisper"
            ) from e
        except Exception as e:
            self.logger.error(f"Erreur chargement Whisper: {e}")
            raise ModelLoadError(f"Erreur chargement Whisper: {e}") from e

    def add_audio(self, audio_chunk: bytes, sample_rate: int = 16000) -> None:
        """Ajoute un chunk audio au buffer."""
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        self.audio_buffer.append(audio_array)
        self.buffer_duration += len(audio_array) / sample_rate

    def transcribe(self, flush: bool = False) -> Optional[str]:
        """
        Transcrit le buffer audio si suffisamment de données.

        Args:
            flush: Force la transcription même avec peu de données.

        Returns:
            Texte transcrit ou None si pas assez de données.
        """
        if not self.audio_buffer:
            return None
        if not flush and self.buffer_duration < self.min_duration:
            return None

        try:
            audio = self.audio_buffer.concat()
            assert audio is not None  # garanti par la check `if not self.audio_buffer`
            audio_float = audio.astype(np.float32) / 32768.0

            # Si un VAD externe a déjà filtré l'audio, on désactive le VAD
            # interne de Whisper pour éviter un double filtrage qui clippe.
            use_internal_vad = self.config.vad_filter and not self.external_vad
            segments, _info = self.model.transcribe(
                audio_float,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=use_internal_vad,
                vad_parameters=(
                    dict(min_silence_duration_ms=500) if use_internal_vad else None
                ),
            )

            text_parts = [segment.text for segment in segments]
            text = " ".join(text_parts).strip()

            self.clear_buffer()
            return text or None
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Erreur transcription: {e}")
            self.clear_buffer()
            return None

    def clear_buffer(self) -> None:
        """Vide le buffer audio (avec overwrite mémoire des chunks)."""
        # secure_clear overwrite chaque numpy array avec des zéros AVANT de
        # libérer la référence. Réduit la fenêtre d'exposition d'un dump
        # mémoire ou d'un résidu de swap. Best-effort sur les pages stables.
        self.audio_buffer.secure_clear()
        # Garde-fou : SecureAudioBuffer remplace `_chunks` par une nouvelle
        # liste vide ; on n'a pas besoin de réassigner self.audio_buffer.
        # Mais si quelqu'un assigne directement, on tolère via duck-typing.
        if not hasattr(self.audio_buffer, "secure_clear"):
            self.audio_buffer = SecureAudioBuffer()
        self.buffer_duration = 0.0

    def set_language(self, language: str) -> None:
        """Change la langue de transcription."""
        self.config.language = language
