"""Tests pour FilePipeline (mode WAV).

Les tests fournissent un VAD/STT/Translator/TTS mocké, ce qui permet de
valider toute l'orchestration WAV → WAV sans torch ni faster-whisper.
"""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.config import AppConfig
from src.file_pipeline import FilePipeline, _load_wav_as_pcm16


pytestmark = pytest.mark.asyncio


def _write_test_wav(path: Path, sample_rate: int, segments) -> None:
    """Génère un WAV synthétique alternant silence et tons.

    segments: liste de tuples (duration_s, amplitude). Amplitude 0 = silence.
    """
    try:
        import soundfile as sf  # type: ignore
    except ImportError:
        pytest.skip("soundfile non installé")

    parts = []
    for duration_s, amplitude in segments:
        n = int(duration_s * sample_rate)
        if amplitude == 0:
            parts.append(np.zeros(n, dtype=np.int16))
        else:
            t = np.linspace(0, duration_s, n, endpoint=False)
            wave = np.sin(2 * np.pi * 440 * t) * amplitude
            parts.append(wave.astype(np.int16))
    audio = np.concatenate(parts)
    sf.write(str(path), audio, sample_rate, subtype="PCM_16")


def _make_pipeline(tmp_path, config=None) -> FilePipeline:
    if config is None:
        config = AppConfig()
        config.vad.backend = "rms"
        config.vad.rms_threshold = 0.005
        config.audio.chunk_size = 1600  # 100 ms à 16 kHz

    input_path = tmp_path / "in.wav"
    output_path = tmp_path / "out.wav"

    # WAV synthétique : 0.3s silence + 1.5s tone + 0.5s silence + 0.8s tone
    _write_test_wav(
        input_path,
        config.audio.sample_rate,
        [(0.3, 0), (1.5, 8000), (0.5, 0), (0.8, 8000)],
    )

    pipeline = FilePipeline(
        config=config,
        input_file=str(input_path),
        output_file=str(output_path),
        source_lang="fr",
        target_lang="en",
        vad=MagicMock(),
        stt=MagicMock(),
        translator=MagicMock(),
        tts=MagicMock(),
    )
    return pipeline


async def test_file_pipeline_basic_flow(tmp_path):
    """Le pipeline doit lire le WAV, appeler VAD/STT/Translator/TTS et
    produire un WAV de sortie."""
    pipeline = _make_pipeline(tmp_path)

    # VAD : True pendant les tons, False pendant les silences
    # On simplifie : alterne True/False de manière à provoquer ≥ 1 flush
    speech_chunks = iter([False, False, False] + [True] * 14 + [False] * 5 +
                          [True] * 8 + [False] * 5)
    pipeline.vad.is_speech = MagicMock(
        side_effect=lambda _chunk: next(speech_chunks, False)
    )

    # STT : add_audio accumule, transcribe(flush=True) renvoie un texte
    def _add_audio(*_a, **_k):
        pipeline.stt.buffer_duration += 0.1

    pipeline.stt.buffer_duration = 0.0
    pipeline.stt.add_audio = MagicMock(side_effect=_add_audio)
    pipeline.stt.transcribe = MagicMock(
        side_effect=lambda flush=False: ("Phrase test" if flush else None)
    )

    # Translator
    pipeline.translator.translate = MagicMock(return_value="Test phrase")

    # TTS : renvoie un signal sinus 200 ms
    sr = pipeline.config.tts.sample_rate
    tts_audio = np.sin(np.linspace(0, 2 * np.pi * 440, sr // 5)).astype(
        np.int16
    ).tobytes()
    pipeline.tts.synthesize = MagicMock(return_value=tts_audio)

    result = await pipeline.run()

    assert result.output_path.exists()
    assert len(result.transcripts) >= 1
    assert result.transcripts[0][1] == "Test phrase"
    assert result.total_audio_duration_s == pytest.approx(3.1, abs=0.1)
    pipeline.translator.translate.assert_called_with(
        "Phrase test", "fr", "en"
    )


async def test_file_pipeline_silence_only_produces_no_output(tmp_path):
    """Si VAD ne détecte jamais de parole, aucun WAV de sortie n'est créé."""
    pipeline = _make_pipeline(tmp_path)

    pipeline.vad.is_speech = MagicMock(return_value=False)
    pipeline.stt.buffer_duration = 0.0
    pipeline.stt.add_audio = MagicMock()
    pipeline.stt.transcribe = MagicMock(return_value=None)
    pipeline.translator.translate = MagicMock()
    pipeline.tts.synthesize = MagicMock()

    result = await pipeline.run()

    assert not result.output_path.exists()
    assert result.transcripts == []
    pipeline.translator.translate.assert_not_called()


async def test_file_pipeline_resamples_input(tmp_path):
    """Si le WAV d'entrée est à 44100 Hz, il doit être ramené à 16 kHz
    avant traitement (assertion sur le tableau chargé)."""
    try:
        import soundfile as sf  # type: ignore  # noqa: F401
    except ImportError:
        pytest.skip("soundfile non installé")

    config = AppConfig()
    config.vad.backend = "rms"
    config.audio.chunk_size = 1024
    input_path = tmp_path / "44k.wav"

    # 1s de bruit à 44100 Hz
    sr = 44100
    _write_test_wav(input_path, sr, [(1.0, 5000)])

    audio_16k = _load_wav_as_pcm16(input_path, target_rate=16000)
    # Durée préservée à ±10 samples
    assert abs(len(audio_16k) - 16000) <= 10


async def test_file_pipeline_missing_input_raises(tmp_path):
    config = AppConfig()
    pipeline = FilePipeline(
        config=config,
        input_file=str(tmp_path / "nonexistent.wav"),
        output_file=str(tmp_path / "out.wav"),
        vad=MagicMock(),
        stt=MagicMock(),
        translator=MagicMock(),
        tts=MagicMock(),
    )
    with pytest.raises(FileNotFoundError):
        await pipeline.run()


async def test_file_pipeline_handles_missing_tts(tmp_path):
    """Si TTS renvoie None (Piper non installé), pas de WAV de sortie mais
    pas de crash non plus."""
    pipeline = _make_pipeline(tmp_path)

    speech_chunks = iter([False] * 3 + [True] * 14 + [False] * 5)
    pipeline.vad.is_speech = MagicMock(
        side_effect=lambda _chunk: next(speech_chunks, False)
    )

    def _add_audio(*_a, **_k):
        pipeline.stt.buffer_duration += 0.1

    pipeline.stt.buffer_duration = 0.0
    pipeline.stt.add_audio = MagicMock(side_effect=_add_audio)
    pipeline.stt.transcribe = MagicMock(
        side_effect=lambda flush=False: ("Phrase" if flush else None)
    )
    pipeline.translator.translate = MagicMock(return_value="Sentence")
    pipeline.tts.synthesize = MagicMock(return_value=None)

    result = await pipeline.run()

    # Pas d'audio TTS donc pas de fichier
    assert not result.output_path.exists()
    # Mais la transcription a quand même eu lieu
    assert len(result.transcripts) >= 1
