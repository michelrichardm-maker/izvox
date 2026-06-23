#!/usr/bin/env python
"""
Diagnostic complet des périphériques audio.

Liste et teste les périphériques disponibles. Utile pour vérifier
que VB-Cable est correctement détecté avant de lancer izvox.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_manager import AudioManager  # noqa: E402


def main() -> None:
    print("\n" + "=" * 70)
    print("🎚️  DIAGNOSTIC AUDIO IZVOX")
    print("=" * 70)

    manager = AudioManager()
    manager.print_devices()

    print("\n📍 RECHERCHE DES PÉRIPHÉRIQUES REQUIS:")
    print("-" * 70)

    try:
        mic = manager.get_default_input_device()
        print(f"✓ Microphone par défaut: {mic.name}")
    except Exception as e:
        print(f"✗ Microphone par défaut: {e}")

    try:
        speakers = manager.get_default_output_device()
        print(f"✓ Haut-parleurs par défaut: {speakers.name}")
    except Exception as e:
        print(f"✗ Haut-parleurs par défaut: {e}")

    try:
        vbcable = manager.find_device("CABLE Input", output_only=True)
        print(f"✓ VB-Cable Input: {vbcable.name}")
    except Exception as e:
        print(f"✗ VB-Cable Input: {e}")

    try:
        vbcable_b = manager.find_loopback_device("CABLE-B")
        print(f"✓ VB-Cable B Loopback: {vbcable_b.name}")
    except Exception as e:
        print(f"⚠ VB-Cable B Loopback: {e}")

    print("-" * 70)
    manager.close_all()


if __name__ == "__main__":
    main()
