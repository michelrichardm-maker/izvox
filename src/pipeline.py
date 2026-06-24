"""
Pipeline de traduction complet.

Orchestre VAD, STT, Translation, TTS pour un flux audio unidirectionnel.
BilingualTranslator gère les deux pipelines (outgoing/incoming) en parallèle.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, List, Optional

from .audio_manager import AudioManager
from .config import AppConfig, FlowDirection
from .security.redaction import maybe_redact
from .stt import STTProcessor
from .translator import TranslatorProcessor
from .tts import TTSProcessor
from .utils import resample_pcm
from .vad import BaseVAD, VADFactory

# Garde-fou anti-mémoire : si l'utilisateur parle plus de N secondes sans
# pause détectable, on flushe quand même pour éviter d'accumuler.
MAX_BUFFER_DURATION_S = 4.0


@dataclass
class PipelineStats:
    """Statistiques d'un pipeline."""
    total_translations: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    def update(self, latency_ms: float) -> None:
        self.total_translations += 1
        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / self.total_translations
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)


class TranslationPipeline:
    """
    Pipeline de traduction unidirectionnel.

    Une instance gère un seul sens (OUTGOING ou INCOMING).
    """

    def __init__(self, direction: FlowDirection, config: AppConfig):
        self.direction = direction
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{direction.value}")

        if direction == FlowDirection.OUTGOING:
            self.source_lang = "fr"
            self.target_lang = "en"
            self.tts_lang = "en"
        else:
            self.source_lang = "en"
            self.target_lang = "fr"
            self.tts_lang = "fr"

        self.audio_manager: Optional[AudioManager] = None
        self.vad: Optional[BaseVAD] = None
        self.stt: Optional[STTProcessor] = None
        self.translator: Optional[TranslatorProcessor] = None
        self.tts: Optional[TTSProcessor] = None

        self.input_stream: Optional[Any] = None
        self.output_stream: Optional[Any] = None

        self.is_running = False
        self.stats = PipelineStats()

        self.on_transcript: Optional[Callable[[str, str, float], None]] = None

    async def initialize(self) -> None:
        """Initialise tous les composants du pipeline."""
        self.logger.info(f"Initialisation pipeline {self.direction.value}...")

        self.audio_manager = AudioManager()

        self.vad = VADFactory.create(
            backend=self.config.vad.backend,
            threshold=self.config.vad.threshold,
            rms_threshold=self.config.vad.rms_threshold,
            sample_rate=self.config.audio.sample_rate,
            min_silence_duration=self.config.vad.min_silence_duration,
        )

        # Fix Bug #1 : utiliser dataclasses.replace() pour créer une COPIE de
        # STTConfig avec la langue spécifique à ce pipeline. Sans ça, les
        # deux pipelines (outgoing FR et incoming EN) partageraient la même
        # référence, et l'init du second écraserait la langue du premier.
        stt_config = replace(self.config.stt, language=self.source_lang)
        # external_vad=True : Silero/RMS filtre déjà en amont, on désactive
        # le VAD interne de Whisper pour éviter de clipper les phrases.
        self.stt = STTProcessor(stt_config, external_vad=True)

        self.translator = TranslatorProcessor(self.config.translation)
        self.tts = TTSProcessor(self.config.tts, language=self.tts_lang)

        await self._setup_audio_streams()

        self.logger.info(f"✓ Pipeline {self.direction.value} initialisé")

    async def _setup_audio_streams(self) -> None:
        audio_config = self.config.audio

        if self.direction == FlowDirection.OUTGOING:
            self.input_stream = self.audio_manager.open_input_stream(
                config=audio_config,
                device_pattern=audio_config.input_device_pattern or None,
                stream_id=f"{self.direction.value}_in",
            )
            self.output_stream = self.audio_manager.open_output_stream(
                config=audio_config,
                device_pattern=audio_config.vbcable_input_pattern,
                stream_id=f"{self.direction.value}_out",
            )
        else:  # INCOMING
            self.input_stream = self.audio_manager.open_loopback_stream(
                config=audio_config,
                device_pattern=audio_config.vbcable_output_pattern,
                stream_id=f"{self.direction.value}_in",
                exclusive=audio_config.loopback_exclusive,
            )
            self.output_stream = self.audio_manager.open_output_stream(
                config=audio_config,
                device_pattern=audio_config.output_device_pattern or None,
                stream_id=f"{self.direction.value}_out",
            )

    async def run(self) -> None:
        """Boucle principale du pipeline.

        Logique de découpe en phrases (fix B2) :
        - Tant que VAD détecte de la parole : on accumule les chunks dans le
          buffer STT.
        - Si on dépasse MAX_BUFFER_DURATION_S sans pause, on flushe quand
          même (garde-fou anti-mémoire pour les locuteurs « one-shot »).
        - Sur la transition speech → silence (l'utilisateur vient de
          s'arrêter), on flushe et on traduit. C'est ça qui rend la latence
          réactive et empêche les phrases collées.
        """
        self.is_running = True
        self.logger.info(f"▶ Démarrage pipeline {self.direction.value}")

        was_speaking = False
        try:
            loop = asyncio.get_running_loop()
            while self.is_running:
                try:
                    audio_chunk = await loop.run_in_executor(
                        None,
                        lambda: self.input_stream.read(
                            self.config.audio.chunk_size,
                            exception_on_overflow=False,
                        ),
                    )

                    is_speech_now = self.vad.is_speech(audio_chunk)

                    if is_speech_now:
                        self.stt.add_audio(
                            audio_chunk, self.config.audio.sample_rate
                        )
                        was_speaking = True
                        # Garde-fou : phrase trop longue sans pause
                        if self.stt.buffer_duration >= MAX_BUFFER_DURATION_S:
                            transcript = self.stt.transcribe(flush=True)
                            if transcript:
                                await self._process_transcript(transcript)
                    elif was_speaking:
                        # Transition parole → silence : c'est la fin d'une phrase
                        transcript = self.stt.transcribe(flush=True)
                        if transcript:
                            await self._process_transcript(transcript)
                        was_speaking = False

                    await asyncio.sleep(0.001)
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self.logger.error(f"Erreur dans la boucle: {e}")
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            self.logger.info(f"⏸ Pipeline {self.direction.value} annulé")
        finally:
            await self.cleanup()

    async def _process_transcript(self, text: str) -> None:
        """Traite une transcription complète: traduction + TTS."""
        # Polish : monotonic au lieu de time.time() pour la latence — évite
        # de retomber en arrière sur un NTP sync (latences négatives ou nulles).
        start_time = time.monotonic()

        redact = getattr(self.config, "redact_logs", True)
        self.logger.info(
            f"[{self.direction.value}] 📝 "
            f"{maybe_redact(text, self.source_lang, redact)}"
        )

        loop = asyncio.get_running_loop()
        translation = await loop.run_in_executor(
            None,
            self.translator.translate,
            text,
            self.source_lang,
            self.target_lang,
        )

        self.logger.info(
            f"[{self.direction.value}] 🔄 "
            f"{maybe_redact(translation, self.target_lang, redact)}"
        )

        if self.tts:
            audio_data = await loop.run_in_executor(
                None, self.tts.synthesize, translation
            )
            if audio_data and self.output_stream:
                # Fix B1 : Piper sort à 22050 Hz, le stream de sortie est
                # à 16000 Hz. Sans rééchantillonnage, la voix sortirait
                # ~26% trop lente.
                if self.config.tts.sample_rate != self.config.audio.sample_rate:
                    audio_data = await loop.run_in_executor(
                        None,
                        resample_pcm,
                        audio_data,
                        self.config.tts.sample_rate,
                        self.config.audio.sample_rate,
                    )
                try:
                    await loop.run_in_executor(
                        None, self.output_stream.write, audio_data
                    )
                except Exception as e:  # noqa: BLE001
                    self.logger.warning(f"Erreur écriture audio: {e}")

        latency_ms = (time.monotonic() - start_time) * 1000
        self.stats.update(latency_ms)

        self.logger.info(
            f"[{self.direction.value}] ⏱ Latence: {latency_ms:.0f}ms"
        )

        if self.on_transcript:
            try:
                self.on_transcript(text, translation, latency_ms)
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"Erreur callback on_transcript: {e}")

    async def cleanup(self) -> None:
        """Libère les ressources."""
        self.is_running = False
        if self.audio_manager:
            self.audio_manager.close_all()
        self.logger.info(
            f"✓ Pipeline {self.direction.value} arrêté "
            f"({self.stats.total_translations} traductions)"
        )

    def get_stats(self) -> dict:
        return {
            "direction": self.direction.value,
            "total_translations": self.stats.total_translations,
            "avg_latency_ms": round(self.stats.avg_latency_ms, 1),
            "min_latency_ms": (
                round(self.stats.min_latency_ms, 1)
                if self.stats.min_latency_ms != float("inf")
                else 0.0
            ),
            "max_latency_ms": round(self.stats.max_latency_ms, 1),
        }


class BilingualTranslator:
    """
    Orchestrateur principal gérant les deux pipelines en parallèle.

    Usage:
        translator = BilingualTranslator(config)
        await translator.start()
        # ...
        await translator.stop()
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.outgoing = TranslationPipeline(FlowDirection.OUTGOING, config)
        self.incoming = TranslationPipeline(FlowDirection.INCOMING, config)

        self.tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Démarre les deux pipelines en parallèle."""
        self.logger.info("=" * 70)
        self.logger.info("🚀 TRADUCTEUR LOCAL BIDIRECTIONNEL - DÉMARRAGE")
        self.logger.info("=" * 70)

        await self.outgoing.initialize()
        await self.incoming.initialize()

        self.logger.info("")
        self.logger.info("✓ Tous les flux sont opérationnels (100% LOCAL)")
        self.logger.info("")
        self.logger.info("📞 OUTGOING: Micro → FR→EN → VB-Cable Input 1 → Teams")
        self.logger.info("📞 INCOMING: Teams → VB-Cable B → EN→FR → Haut-parleurs")
        self.logger.info("")
        self.logger.info("💰 Coût: $0.00 | 🔒 Données: 100% privées")
        self.logger.info("")
        self.logger.info("Appuyez sur Ctrl+C pour arrêter")
        self.logger.info("=" * 70)

        self.tasks = [
            asyncio.create_task(self.outgoing.run()),
            asyncio.create_task(self.incoming.run()),
        ]

        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def stop(self) -> None:
        """Arrête proprement les pipelines."""
        self.logger.info("\n🛑 Arrêt en cours...")
        for task in self.tasks:
            task.cancel()
        await self.outgoing.cleanup()
        await self.incoming.cleanup()
        self.logger.info("✓ Arrêt complet")

    def get_stats(self) -> dict:
        return {
            "outgoing": self.outgoing.get_stats(),
            "incoming": self.incoming.get_stats(),
        }
