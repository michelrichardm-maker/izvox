"""
FilePipeline — mode WAV → WAV.

Permet de tester tout le pipeline (VAD → STT → traduction → TTS) sur des
fichiers audio, sans matériel audio ni VB-Cable. C'est l'équivalent en
mode dev/CI du `TranslationPipeline` qui, lui, dépend de PyAudioWPatch.

Workflow :
  1. Lit un WAV (n'importe quel sample-rate, mono ou stéréo)
  2. Le ramène à 16 kHz mono int16 (downmix + rééchantillonnage)
  3. Le traite chunk par chunk avec la même logique que le pipeline temps
     réel (VAD → buffer STT → flush sur transition speech→silence)
  4. À la fin du fichier, flushe le dernier segment.
  5. Concatène tout l'audio TTS produit dans un WAV de sortie (16 kHz par
     défaut, ou le sample-rate de Piper si on veut éviter le resample).

Usage standalone :
    pipeline = FilePipeline(
        config=app_config,
        input_file="samples/fr.wav",
        output_file="out_en.wav",
        source_lang="fr",
        target_lang="en",
    )
    await pipeline.run()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

from dataclasses import replace

from .config import AppConfig
from .pipeline import MAX_BUFFER_DURATION_S, PipelineStats
from .security.redaction import maybe_redact
from .stt import STTProcessor
from .translator import TranslatorProcessor
from .tts import TTSProcessor
from .utils import resample_pcm
from .vad import BaseVAD, VADFactory


@dataclass
class FilePipelineResult:
    """Résultat d'une exécution FilePipeline."""
    output_path: Path
    transcripts: List[tuple]  # list de (source_text, translated_text, latency_ms)
    stats: PipelineStats
    total_audio_duration_s: float
    total_processing_time_s: float


def _load_wav_as_pcm16(path: Path, target_rate: int = 16000) -> np.ndarray:
    """Charge un WAV et retourne du int16 mono au target_rate."""
    try:
        import soundfile as sf  # type: ignore
    except ImportError as e:
        raise ImportError(
            "soundfile est requis pour le mode fichier WAV. "
            "Installez-le avec: pip install soundfile"
        ) from e

    data, src_rate = sf.read(str(path), dtype="int16", always_2d=False)

    # Downmix stéréo → mono si nécessaire
    if data.ndim == 2:
        data = data.mean(axis=1).astype(np.int16)

    # Rééchantillonnage si nécessaire
    if src_rate != target_rate:
        data = np.frombuffer(
            resample_pcm(data.tobytes(), src_rate, target_rate),
            dtype=np.int16,
        ).copy()

    return data


def _write_wav_pcm16(path: Path, audio: bytes, sample_rate: int) -> None:
    """Écrit un PCM int16 en WAV. Utilise soundfile si dispo, sinon stdlib."""
    arr = np.frombuffer(audio, dtype=np.int16)
    try:
        import soundfile as sf  # type: ignore
        sf.write(str(path), arr, sample_rate, subtype="PCM_16")
    except ImportError:
        # Fallback stdlib (limité mais suffisant pour mono int16)
        import wave
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)


class FilePipeline:
    """
    Pipeline de traduction WAV → WAV pour le dev/test.

    Utilise les mêmes composants que TranslationPipeline (VAD, STT,
    Translator, TTS) mais lit/écrit des fichiers au lieu de streams audio.
    """

    def __init__(
        self,
        config: AppConfig,
        input_file: str,
        output_file: str,
        source_lang: str = "fr",
        target_lang: str = "en",
        # Composants optionnels (utiles pour les tests qui veulent mocker)
        vad: Optional[BaseVAD] = None,
        stt: Optional[STTProcessor] = None,
        translator: Optional[TranslatorProcessor] = None,
        tts: Optional[TTSProcessor] = None,
    ):
        self.config = config
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.tts_lang = target_lang
        self.logger = logging.getLogger(__name__)

        self.vad = vad
        self.stt = stt
        self.translator = translator
        self.tts = tts

        self.stats = PipelineStats()
        self.transcripts: List[tuple] = []
        # Audio TTS accumulé, écrit en une passe à la fin
        self._output_chunks: List[bytes] = []
        # Sample-rate du WAV de sortie. Par défaut = audio.sample_rate, mais
        # on peut envisager une option future pour garder le SR Piper natif.
        self._output_rate = config.audio.sample_rate

    def initialize(self) -> None:
        """Charge les composants non fournis (modèles)."""
        if self.vad is None:
            self.vad = VADFactory.create(
                backend=self.config.vad.backend,
                threshold=self.config.vad.threshold,
                rms_threshold=self.config.vad.rms_threshold,
                sample_rate=self.config.audio.sample_rate,
                min_silence_duration=self.config.vad.min_silence_duration,
            )

        if self.stt is None:
            # Fix Bug #1 : COPIE de STTConfig pour ne pas muter la config
            # partagée (cf. pipeline.py).
            stt_config = replace(self.config.stt, language=self.source_lang)
            self.stt = STTProcessor(stt_config, external_vad=True)

        if self.translator is None:
            self.translator = TranslatorProcessor(self.config.translation)

        if self.tts is None:
            self.tts = TTSProcessor(self.config.tts, language=self.tts_lang)

    async def run(self) -> FilePipelineResult:
        """Traite le fichier d'entrée et écrit le fichier de sortie."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Fichier d'entrée introuvable: {self.input_file}")

        if any(c is None for c in (self.vad, self.stt, self.translator)):
            self.initialize()

        self.logger.info(f"📁 Chargement {self.input_file}")
        audio = _load_wav_as_pcm16(self.input_file, target_rate=self.config.audio.sample_rate)
        sample_rate = self.config.audio.sample_rate
        total_duration_s = len(audio) / sample_rate
        self.logger.info(
            f"   → {len(audio)} samples, {total_duration_s:.2f}s, {sample_rate}Hz"
        )

        start_time = time.time()
        chunk_size = self.config.audio.chunk_size
        was_speaking = False

        # Itère sur les chunks
        for offset in range(0, len(audio), chunk_size):
            chunk = audio[offset:offset + chunk_size]
            if len(chunk) == 0:
                continue
            chunk_bytes = chunk.tobytes()

            is_speech_now = self.vad.is_speech(chunk_bytes)

            if is_speech_now:
                self.stt.add_audio(chunk_bytes, sample_rate)
                was_speaking = True
                if self.stt.buffer_duration >= MAX_BUFFER_DURATION_S:
                    transcript = self.stt.transcribe(flush=True)
                    if transcript:
                        await self._process_transcript(transcript)
            elif was_speaking:
                transcript = self.stt.transcribe(flush=True)
                if transcript:
                    await self._process_transcript(transcript)
                was_speaking = False

            # Yield aux autres tâches asyncio si jamais le pipeline tourne en
            # parallèle d'autre chose. Sinon c'est quasi gratuit.
            await asyncio.sleep(0)

        # Fin du fichier : flushe ce qui reste dans le buffer STT
        if self.stt.buffer_duration > 0:
            transcript = self.stt.transcribe(flush=True)
            if transcript:
                await self._process_transcript(transcript)

        # Écriture du fichier de sortie
        if self._output_chunks:
            combined = b"".join(self._output_chunks)
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            _write_wav_pcm16(self.output_file, combined, self._output_rate)
            self.logger.info(
                f"📁 {self.output_file} écrit "
                f"({len(combined) // 2 / self._output_rate:.2f}s)"
            )
        else:
            self.logger.warning(
                "Aucun audio TTS produit (rien transcrit, ou TTS indisponible)"
            )

        return FilePipelineResult(
            output_path=self.output_file,
            transcripts=list(self.transcripts),
            stats=self.stats,
            total_audio_duration_s=total_duration_s,
            total_processing_time_s=time.time() - start_time,
        )

    async def _process_transcript(self, text: str) -> None:
        """Traite une transcription : traduction → TTS → accumulation."""
        start_time = time.time()
        redact = getattr(self.config, "redact_logs", True)
        self.logger.info(f"📝 {maybe_redact(text, self.source_lang, redact)}")

        loop = asyncio.get_running_loop()
        translation = await loop.run_in_executor(
            None,
            self.translator.translate,
            text,
            self.source_lang,
            self.target_lang,
        )
        self.logger.info(f"🔄 {maybe_redact(translation, self.target_lang, redact)}")

        if self.tts:
            audio_data = await loop.run_in_executor(
                None, self.tts.synthesize, translation
            )
            if audio_data:
                # Resample si Piper et la sortie ne sont pas alignés
                if self.config.tts.sample_rate != self._output_rate:
                    audio_data = resample_pcm(
                        audio_data,
                        self.config.tts.sample_rate,
                        self._output_rate,
                    )
                self._output_chunks.append(audio_data)

        latency_ms = (time.time() - start_time) * 1000
        self.stats.update(latency_ms)
        self.transcripts.append((text, translation, latency_ms))
        self.logger.info(f"⏱ Latence: {latency_ms:.0f}ms")
