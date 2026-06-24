"""
Text-to-Speech avec Piper.

Synthétise la parole à partir du texte traduit, en streaming ONNX.
Voix françaises et anglaises téléchargées automatiquement par ModelManager.
"""

import logging
from pathlib import Path
from typing import Generator, Optional

from .config import TTSConfig


class TTSProcessor:
    """
    Processeur Text-to-Speech basé sur Piper.

    Usage:
        tts = TTSProcessor(config, language="en")
        audio_data = tts.synthesize("Hello world")
    """

    def __init__(self, config: TTSConfig, language: str = "fr"):
        self.config = config
        self.language = language
        self.logger = logging.getLogger(__name__)

        self.voice = None
        self._load_voice()

    def _load_voice(self) -> None:
        """Charge la voix Piper pour la langue configurée."""
        try:
            from piper import PiperVoice  # type: ignore
        except ImportError:
            self.logger.warning(
                "Piper TTS non installé. Installez avec: pip install piper-tts"
            )
            self.voice = None
            return

        voice_name = (
            self.config.voice_fr if self.language == "fr" else self.config.voice_en
        )
        model_path = Path(self.config.model_path) / voice_name
        onnx_file = model_path / f"{voice_name}.onnx"

        if not onnx_file.exists():
            self.logger.warning(f"Voix Piper non trouvée: {onnx_file}")
            self.logger.warning(
                "Lancez `python tools/download_models.py` pour télécharger les voix."
            )
            self.voice = None
            return

        try:
            self.voice = PiperVoice.load(str(onnx_file))
            self.logger.info(f"✓ Piper TTS chargé ({self.language})")
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Erreur chargement Piper: {e}")
            self.voice = None

    def _iter_pcm_chunks(self, text: str) -> Generator[bytes, None, None]:
        """Itère sur les chunks PCM int16 produits par Piper.

        Gère les deux API connues :
        - piper-tts ≤ 1.2.x : `voice.synthesize_stream_raw(text)` renvoie
          directement des `bytes`.
        - piper-tts ≥ 1.3.x : `voice.synthesize(text)` renvoie des objets
          `AudioChunk` dont l'attribut `audio_int16_bytes` contient le PCM.
        """
        if hasattr(self.voice, "synthesize_stream_raw"):
            yield from self.voice.synthesize_stream_raw(text)
            return
        for chunk in self.voice.synthesize(text):
            audio_bytes = getattr(chunk, "audio_int16_bytes", None)
            if audio_bytes is None:
                # Fallback : reconstruit depuis l'array numpy si dispo
                arr = getattr(chunk, "audio_int16_array", None)
                if arr is not None:
                    audio_bytes = arr.tobytes()
            if audio_bytes:
                yield audio_bytes

    def synthesize(self, text: str) -> Optional[bytes]:
        """Synthétise du texte en audio (int16 PCM)."""
        if not text or not text.strip():
            return None
        if not self.voice:
            self.logger.warning("TTS non disponible")
            return None
        try:
            audio_chunks = list(self._iter_pcm_chunks(text))
            if not audio_chunks:
                return None
            return b"".join(audio_chunks)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Erreur synthèse TTS: {e}")
            return None

    def synthesize_stream(self, text: str) -> Generator[bytes, None, None]:
        """Synthétise du texte en streaming (chunks PCM int16)."""
        if not text or not self.voice:
            return
        try:
            yield from self._iter_pcm_chunks(text)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Erreur streaming TTS: {e}")

    def set_language(self, language: str) -> None:
        """Change la langue de synthèse et recharge la voix."""
        if language != self.language:
            self.language = language
            self._load_voice()
