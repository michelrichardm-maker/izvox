#!/usr/bin/env python
"""
Test rapide de la traduction FR↔EN.

Permet de vérifier que les modèles fonctionnent en mode REPL.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AppConfig  # noqa: E402
from src.model_manager import ModelManager  # noqa: E402
from src.translator import TranslatorProcessor  # noqa: E402


def main() -> None:
    print("=" * 70)
    print("🔄 TEST DE TRADUCTION FR ↔ EN")
    print("=" * 70)

    config = AppConfig()
    manager = ModelManager(config, auto_detect=True)
    manager.initialize(verbose=False)

    print("\nChargement du modèle...")
    translator = TranslatorProcessor(config.translation)

    print("\n✓ Prêt!")
    print("Entrez du texte en français pour le traduire en anglais.")
    print("Préfixez par 'en:' pour traduire de l'anglais vers le français.")
    print("Tapez 'quit' pour quitter.\n")

    while True:
        try:
            text = input("→ ").strip()
            if text.lower() in {"quit", "exit", "q"}:
                break
            if not text:
                continue
            if text.lower().startswith("en:"):
                text = text[3:].strip()
                result = translator.translate(text, "en", "fr")
                print(f"← {result}\n")
            else:
                result = translator.translate(text, "fr", "en")
                print(f"← {result}\n")
        except (KeyboardInterrupt, EOFError):
            break

    print("\nAu revoir!")


if __name__ == "__main__":
    main()
