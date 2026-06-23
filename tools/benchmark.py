#!/usr/bin/env python
"""
Benchmark de performance du système izvox.

Mesure la latence de chaque composant (STT, traduction, TTS).
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AppConfig  # noqa: E402
from src.model_manager import ModelManager  # noqa: E402


def benchmark_stt(config: AppConfig) -> float:
    print("\n🎤 Benchmark STT (Faster-Whisper)...")
    from src.stt import STTProcessor
    stt = STTProcessor(config.stt)

    duration = 3.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    audio = np.random.randint(-1000, 1000, samples, dtype=np.int16)
    audio_bytes = audio.tobytes()

    stt.add_audio(audio_bytes, sample_rate)
    start = time.time()
    stt.transcribe(flush=True)
    elapsed = (time.time() - start) * 1000

    print(f"   Durée audio: {duration}s")
    print(f"   Temps traitement: {elapsed:.0f}ms")
    print(f"   Ratio: {elapsed / (duration * 1000):.2f}x temps réel")
    return elapsed


def benchmark_translation(config: AppConfig) -> float:
    print("\n🔄 Benchmark Traduction (NLLB / Opus-MT)...")
    from src.translator import TranslatorProcessor
    translator = TranslatorProcessor(config.translation)

    test_texts = [
        "Bonjour, comment allez-vous?",
        "Je voudrais commander cinq cents unités du produit référence XYZ.",
        "Le délai de livraison est de trois semaines après confirmation.",
    ]

    total_time = 0.0
    for text in test_texts:
        start = time.time()
        translator.translate(text, "fr", "en")
        elapsed = (time.time() - start) * 1000
        total_time += elapsed
        print(f"   '{text[:40]}...' → {elapsed:.0f}ms")

    avg_time = total_time / len(test_texts)
    print(f"\n   Temps moyen: {avg_time:.0f}ms")
    return avg_time


def benchmark_tts(config: AppConfig) -> float:
    print("\n🔊 Benchmark TTS (Piper)...")
    try:
        from src.tts import TTSProcessor
        tts = TTSProcessor(config.tts, language="en")
        if not tts.voice:
            print("   ⚠ Piper non disponible (voix non téléchargée?)")
            return 0.0

        test_text = "Hello, this is a test of the text to speech system."
        start = time.time()
        audio = tts.synthesize(test_text)
        elapsed = (time.time() - start) * 1000

        if audio:
            audio_duration = len(audio) / (22050 * 2) * 1000
            print(f"   Texte: {len(test_text)} caractères")
            print(f"   Audio généré: {audio_duration:.0f}ms")
            print(f"   Temps traitement: {elapsed:.0f}ms")
        return elapsed
    except ImportError:
        print("   ⚠ Piper non installé")
        return 0.0


def main() -> None:
    print("=" * 70)
    print("⏱️  BENCHMARK DE PERFORMANCE IZVOX")
    print("=" * 70)

    config = AppConfig()
    manager = ModelManager(config, auto_detect=True)
    manager.initialize(verbose=True)

    stt_time = benchmark_stt(config)
    translation_time = benchmark_translation(config)
    tts_time = benchmark_tts(config)

    total_time = stt_time + translation_time + tts_time

    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print(f"STT:         {stt_time:.0f}ms")
    print(f"Traduction:  {translation_time:.0f}ms")
    print(f"TTS:         {tts_time:.0f}ms")
    print("-" * 70)
    print(f"TOTAL:       {total_time:.0f}ms")
    print("=" * 70)

    if total_time < 600:
        print("✓ Latence excellente (<600ms)")
    elif total_time < 1000:
        print("✓ Latence acceptable (<1000ms)")
    else:
        print("⚠ Latence élevée (>1000ms)")
        print("  Suggestions: réduire taille modèles, utiliser GPU")


if __name__ == "__main__":
    main()
