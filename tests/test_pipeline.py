"""Tests pour le pipeline.

Couvre :
- PipelineStats
- Constantes / énumérations
- Fix B2 : transition speech→silence via VAD doit déclencher un flush
  STT et un call à `_process_transcript`.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import FlowDirection
from src.pipeline import MAX_BUFFER_DURATION_S, PipelineStats, TranslationPipeline


def test_pipeline_stats_initial():
    stats = PipelineStats()
    assert stats.total_translations == 0
    assert stats.avg_latency_ms == 0.0
    assert stats.min_latency_ms == float("inf")
    assert stats.max_latency_ms == 0.0


def test_pipeline_stats_update():
    stats = PipelineStats()
    stats.update(100.0)
    stats.update(200.0)
    stats.update(50.0)
    assert stats.total_translations == 3
    assert stats.avg_latency_ms == pytest.approx(350.0 / 3)
    assert stats.min_latency_ms == 50.0
    assert stats.max_latency_ms == 200.0


def test_flow_direction_values():
    assert FlowDirection.OUTGOING.value == "outgoing"
    assert FlowDirection.INCOMING.value == "incoming"


def test_max_buffer_duration_sane():
    """Le garde-fou anti-mémoire doit rester dans une plage raisonnable."""
    assert 1.0 <= MAX_BUFFER_DURATION_S <= 10.0


# ---------------------------------------------------------------------------
# Fix B2 : transition speech → silence flushe le STT
# ---------------------------------------------------------------------------


def _make_pipeline_for_run_test(speech_pattern, transcripts):
    """Construit un TranslationPipeline avec tous les composants mockés.

    Args:
        speech_pattern: liste de booléens, valeur de retour de vad.is_speech
            pour chaque appel.
        transcripts: liste des chaînes que stt.transcribe(flush=True) renvoie
            successivement.
    """
    import logging

    # Bypass __init__ pour éviter de charger les vrais modèles
    pipeline = TranslationPipeline.__new__(TranslationPipeline)
    pipeline.direction = FlowDirection.OUTGOING
    pipeline.source_lang = "fr"
    pipeline.target_lang = "en"
    pipeline.tts_lang = "en"
    pipeline.stats = PipelineStats()
    pipeline.on_transcript = None
    pipeline.is_running = True
    pipeline.audio_manager = MagicMock()
    pipeline.logger = logging.getLogger("test_pipeline")

    # Config mockée
    config = MagicMock()
    config.audio.chunk_size = 1024
    config.audio.sample_rate = 16000
    pipeline.config = config

    # VAD mocké : renvoie successivement les valeurs de speech_pattern
    pipeline.vad = MagicMock()
    pipeline.vad.is_speech = MagicMock(side_effect=list(speech_pattern))

    # STT mocké : add_audio incrémente buffer_duration ; transcribe renvoie
    # successivement les valeurs de transcripts.
    pipeline.stt = MagicMock()
    pipeline.stt.buffer_duration = 0.0
    pipeline.stt.transcribe = MagicMock(side_effect=list(transcripts))

    def _add_audio(*_args, **_kw):
        pipeline.stt.buffer_duration += 0.1  # +100ms par chunk simulé

    pipeline.stt.add_audio = MagicMock(side_effect=_add_audio)

    # Stream d'entrée : renvoie un chunk dummy à chaque read
    pipeline.input_stream = MagicMock()
    pipeline.input_stream.read = MagicMock(return_value=b"\x00\x00" * 512)

    # _process_transcript et cleanup mockés
    pipeline._process_transcript = AsyncMock()
    pipeline.cleanup = AsyncMock()

    return pipeline


async def _run_for_n_iterations(pipeline, n: int):
    """Lance pipeline.run() puis l'arrête après n itérations."""
    task = asyncio.create_task(pipeline.run())
    # Laisse n itérations s'exécuter (sleep entre chaque)
    await asyncio.sleep(0.05 * n)
    pipeline.is_running = False
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        task.cancel()


@pytest.mark.asyncio
async def test_speech_to_silence_transition_triggers_flush():
    """Fix B2 : quand VAD passe de True à False, le STT doit être flushé
    et _process_transcript appelé."""
    # 3 chunks de parole, puis 2 de silence
    speech_pattern = [True, True, True, False, False] + [False] * 50
    transcripts = ["Bonjour le monde"] + [None] * 50

    pipeline = _make_pipeline_for_run_test(speech_pattern, transcripts)
    await _run_for_n_iterations(pipeline, 6)

    # Au moins un appel à transcribe(flush=True) ET un appel à _process_transcript
    flush_calls = [
        c for c in pipeline.stt.transcribe.call_args_list
        if c.kwargs.get("flush") is True or (c.args and c.args[0] is True)
    ]
    assert len(flush_calls) >= 1
    pipeline._process_transcript.assert_awaited()
    pipeline._process_transcript.assert_called_with("Bonjour le monde")


@pytest.mark.asyncio
async def test_silence_only_does_not_flush():
    """Si VAD ne détecte jamais de parole, on ne doit jamais flusher."""
    speech_pattern = [False] * 50
    transcripts = [None] * 50

    pipeline = _make_pipeline_for_run_test(speech_pattern, transcripts)
    await _run_for_n_iterations(pipeline, 5)

    pipeline.stt.transcribe.assert_not_called()
    pipeline._process_transcript.assert_not_awaited()


@pytest.mark.asyncio
async def test_long_speech_triggers_max_buffer_flush():
    """Si on dépasse MAX_BUFFER_DURATION_S sans pause, on flushe quand même."""
    # Toujours de la parole, mais on simule un buffer qui croît
    speech_pattern = [True] * 100
    transcripts = ["Une très longue phrase"] + [None] * 100

    pipeline = _make_pipeline_for_run_test(speech_pattern, transcripts)
    # Forcer buffer_duration à dépasser le seuil dès la 1ère itération
    original_add = pipeline.stt.add_audio.side_effect

    def _grow_fast(*args, **kw):
        original_add(*args, **kw)
        pipeline.stt.buffer_duration = MAX_BUFFER_DURATION_S + 1.0

    pipeline.stt.add_audio = MagicMock(side_effect=_grow_fast)

    await _run_for_n_iterations(pipeline, 3)

    pipeline._process_transcript.assert_awaited()
    pipeline._process_transcript.assert_called_with("Une très longue phrase")
