#!/usr/bin/env python
"""
Téléchargement manuel des modèles izvox.

Pré-télécharge tous les modèles requis (Whisper, NLLB, Piper) selon le
matériel détecté. Utile pour une installation offline-ready.

Usage:
    python tools/download_models.py
    python tools/download_models.py --profile high_performance
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AppConfig  # noqa: E402
from src.model_manager import ModelManager  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pré-télécharge les modèles izvox."
    )
    parser.add_argument(
        "--profile", "-p",
        choices=["high_performance", "balanced", "low_resource", "cpu_only"],
        default=None,
        help="Profil à utiliser (défaut: détection auto)",
    )
    parser.add_argument(
        "--whisper-only", action="store_true",
        help="Ne télécharge que le modèle Whisper",
    )
    parser.add_argument(
        "--nllb-only", action="store_true",
        help="Ne télécharge que le modèle de traduction",
    )
    parser.add_argument(
        "--piper-only", action="store_true",
        help="Ne télécharge que les voix Piper",
    )
    return parser.parse_args()


def download_whisper(config: AppConfig) -> None:
    print(f"\n📥 Téléchargement Whisper {config.stt.model_size}...")
    try:
        from faster_whisper import WhisperModel  # type: ignore
        WhisperModel(
            config.stt.model_size,
            device="cpu",  # télécharge en CPU pour éviter de bloquer le GPU
            compute_type="int8",
            download_root=config.stt.download_root,
        )
        print("   ✓ Whisper téléchargé")
    except Exception as e:  # noqa: BLE001
        print(f"   ✗ Erreur: {e}")


def download_translation(config: AppConfig) -> None:
    print(f"\n📥 Téléchargement {config.translation.model_name}...")
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # type: ignore
        AutoTokenizer.from_pretrained(
            config.translation.model_name,
            cache_dir=config.translation.cache_dir,
        )
        AutoModelForSeq2SeqLM.from_pretrained(
            config.translation.model_name,
            cache_dir=config.translation.cache_dir,
        )
        print("   ✓ Modèle de traduction téléchargé")
    except Exception as e:  # noqa: BLE001
        print(f"   ✗ Erreur: {e}")


def download_piper(config: AppConfig, manager: ModelManager) -> None:
    print("\n📥 Téléchargement voix Piper...")
    try:
        manager._setup_piper()  # type: ignore[attr-defined]
        print("   ✓ Voix Piper téléchargées")
    except Exception as e:  # noqa: BLE001
        print(f"   ✗ Erreur: {e}")


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("📥 TÉLÉCHARGEMENT DES MODÈLES IZVOX")
    print("=" * 70)

    config = AppConfig()
    manager = ModelManager(config, auto_detect=True)

    if args.profile:
        config.apply_profile(args.profile)
        print(f"\n🎯 Profil forcé: {args.profile}")
    else:
        print(f"\n🎯 Profil auto-détecté: {config.hardware_level.value}")

    only_whisper = args.whisper_only
    only_nllb = args.nllb_only
    only_piper = args.piper_only
    all_components = not any([only_whisper, only_nllb, only_piper])

    if all_components or only_whisper:
        download_whisper(config)
    if all_components or only_nllb:
        download_translation(config)
    if all_components or only_piper:
        download_piper(config, manager)

    print("\n" + "=" * 70)
    print("✓ TÉLÉCHARGEMENT TERMINÉ")
    print("=" * 70)
    print("\nVous pouvez maintenant lancer:")
    print("   python -m src.main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
