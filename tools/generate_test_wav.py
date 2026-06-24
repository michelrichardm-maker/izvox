#!/usr/bin/env python
"""
Génère des fichiers WAV de test via Piper.

Utile pour valider le mode fichier d'izvox sans micro :

    # Génère samples/sample_fr.wav et samples/sample_en.wav (par défaut)
    python tools/generate_test_wav.py

    # Phrase ad-hoc en français
    python tools/generate_test_wav.py --text "Bonjour, comment allez-vous ?" \
                                       --output mon_test.wav --lang fr

    # Phrase ad-hoc en anglais
    python tools/generate_test_wav.py --text "Hello, how are you?" \
                                       --output hello.wav --lang en

Le WAV produit peut être passé directement à izvox :

    python -m src.main --input-file samples/sample_fr.wav \
                       --output-file out_en.wav

Prérequis : la voix Piper correspondante doit être téléchargée
(`python tools/download_models.py --piper-only`).
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import TTSConfig  # noqa: E402
from src.tts import TTSProcessor  # noqa: E402


# Phrases canoniques utilisées en mode défaut
DEFAULT_SENTENCES = {
    "fr": (
        "Bonjour, je suis ravi de vous parler aujourd'hui. "
        "Nous allons discuter du contrat et des délais de livraison. "
        "Avez-vous des questions ?"
    ),
    "en": (
        "Hello, I am pleased to speak with you today. "
        "Let's go over the contract and the delivery timeline. "
        "Do you have any questions?"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Génère un WAV de test via Piper."
    )
    parser.add_argument(
        "--text", "-t", type=str, default=None,
        help="Texte à synthétiser (sinon utilise la phrase canonique).",
    )
    parser.add_argument(
        "--lang", "-l", choices=["fr", "en"], default="fr",
        help="Langue de la voix (défaut: fr).",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Chemin du WAV de sortie (défaut: samples/sample_<lang>.wav).",
    )
    parser.add_argument(
        "--model-path", type=str, default="./models/piper",
        help="Répertoire contenant les voix Piper.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Génère les deux WAV par défaut (FR + EN) en une commande.",
    )
    return parser.parse_args()


def _write_wav(path: Path, audio_bytes: bytes, sample_rate: int) -> None:
    """Écrit du PCM int16 en WAV. soundfile préféré, fallback stdlib."""
    arr = np.frombuffer(audio_bytes, dtype=np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import soundfile as sf  # type: ignore
        sf.write(str(path), arr, sample_rate, subtype="PCM_16")
    except ImportError:
        import wave
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)


def _synthesize_one(lang: str, text: str, output: Path, model_path: str) -> int:
    """Synthétise un WAV. Retourne le code de sortie (0 = OK)."""
    config = TTSConfig(model_path=model_path)
    tts = TTSProcessor(config, language=lang)

    if not tts.voice:
        print(f"❌ Voix Piper {lang} introuvable sous {model_path}/")
        voice_name = config.voice_fr if lang == "fr" else config.voice_en
        print(f"   Lancez : python tools/download_models.py --piper-only")
        print(f"   (cible : {voice_name})")
        return 2

    print(f"🔊 Synthèse {lang.upper()} : \"{text[:60]}{'…' if len(text) > 60 else ''}\"")
    audio = tts.synthesize(text)
    if not audio:
        print("❌ Échec de la synthèse (audio vide).")
        return 1

    sample_rate = config.sample_rate  # 22050 par défaut
    _write_wav(output, audio, sample_rate)

    duration_s = len(audio) / (sample_rate * 2)  # int16 = 2 bytes
    print(f"✓ {output} écrit ({duration_s:.2f}s, {sample_rate}Hz)")
    return 0


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("🔊 GÉNÉRATEUR DE WAV DE TEST")
    print("=" * 70)

    if args.all:
        if args.text or args.output:
            print(
                "⚠ --all ignore --text et --output, "
                "génère les deux fichiers canoniques."
            )
        rc = 0
        for lang in ("fr", "en"):
            output = Path(f"samples/sample_{lang}.wav")
            rc |= _synthesize_one(
                lang, DEFAULT_SENTENCES[lang], output, args.model_path
            )
        return rc

    text = args.text if args.text is not None else DEFAULT_SENTENCES[args.lang]
    output = Path(args.output) if args.output else Path(
        f"samples/sample_{args.lang}.wav"
    )
    return _synthesize_one(args.lang, text, output, args.model_path)


if __name__ == "__main__":
    sys.exit(main())
