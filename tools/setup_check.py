#!/usr/bin/env python
"""
Vérification complète de l'installation izvox.

À exécuter après l'installation pour valider que tout fonctionne.
"""

import sys
from pathlib import Path

# Permet d'exécuter le script depuis n'importe quel répertoire
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_python_version() -> bool:
    """Vérifie la version Python."""
    print("\n📍 Vérification Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"   ✗ Python {version.major}.{version.minor} (requis: 3.10+)")
    return False


def check_dependencies() -> bool:
    """Vérifie les dépendances Python."""
    print("\n📦 Vérification des dépendances...")
    dependencies = {
        "torch": ("PyTorch", True),
        "faster_whisper": ("Faster-Whisper (STT)", True),
        "transformers": ("Transformers (Traduction)", True),
        "pyaudiowpatch": ("PyAudioWPatch (Audio)", True),
        "numpy": ("NumPy", True),
        "yaml": ("PyYAML", True),
        "piper": ("Piper TTS", False),
        "psutil": ("psutil", False),
        "colorlog": ("colorlog", False),
    }

    all_ok = True
    for module, (description, required) in dependencies.items():
        try:
            __import__(module)
            print(f"   ✓ {description}")
        except ImportError:
            if required:
                print(f"   ✗ {description} - MANQUANT (requis)")
                all_ok = False
            else:
                print(f"   ⚠ {description} - non installé (optionnel)")
    return all_ok


def check_cuda() -> bool:
    """Vérifie le support CUDA."""
    print("\n🖥️  Vérification GPU...")
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory // (1024 ** 3)
            print(f"   ✓ CUDA disponible: {gpu_name} ({vram}GB)")
            return True
        print("   ⚠ CUDA non disponible (mode CPU sera utilisé)")
        return True
    except ImportError:
        print("   ⚠ PyTorch non installé")
        return False


def check_vbcable() -> bool:
    """Vérifie l'installation de VB-Cable."""
    print("\n🎚️  Vérification VB-Cable...")
    try:
        import pyaudiowpatch as pyaudio
        p = pyaudio.PyAudio()
        vb_cable_found = False
        vb_cable_b_found = False
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            name_lower = info["name"].lower()
            if "cable input" in name_lower and "vb-audio" in name_lower:
                vb_cable_found = True
            if "cable-b" in name_lower:
                vb_cable_b_found = True
        p.terminate()

        if vb_cable_found:
            print("   ✓ VB-Cable (principal) installé")
        else:
            print("   ✗ VB-Cable (principal) NON TROUVÉ")
            print("     → Installer depuis: https://vb-audio.com/Cable/")
        if vb_cable_b_found:
            print("   ✓ VB-Cable B (secondaire) installé")
        else:
            print("   ⚠ VB-Cable B (secondaire) non trouvé")
            print("     → Recommandé pour le flux entrant")
        return vb_cable_found
    except ImportError:
        print("   ✗ PyAudioWPatch non installé")
        return False
    except Exception as e:
        print(f"   ⚠ Vérification VB-Cable impossible: {e}")
        return False


def check_models() -> bool:
    """Vérifie la présence des modèles."""
    print("\n🤖 Vérification des modèles...")
    models_dir = Path("./models")
    whisper_ok = (models_dir / "whisper").exists()
    nllb_ok = (models_dir / "nllb").exists()
    piper_ok = (models_dir / "piper").exists()

    print(
        "   ✓ Whisper: dossier présent"
        if whisper_ok
        else "   ⚠ Whisper: sera téléchargé au premier lancement"
    )
    print(
        "   ✓ NLLB: dossier présent"
        if nllb_ok
        else "   ⚠ NLLB: sera téléchargé au premier lancement"
    )
    print(
        "   ✓ Piper: dossier présent"
        if piper_ok
        else "   ⚠ Piper: sera téléchargé au premier lancement"
    )
    return True


def print_summary(results: dict) -> None:
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DE L'INSTALLATION")
    print("=" * 70)
    all_ok = all(results.values())
    for test, result in results.items():
        status = "✓" if result else "✗"
        print(f"   {status} {test}")
    print("=" * 70)
    if all_ok:
        print("\n🎉 INSTALLATION COMPLÈTE !")
        print("\nPour démarrer:")
        print("   python -m src.main")
        print("\nOu avec les scripts:")
        print("   .\\scripts\\run.bat  (Windows)")
    else:
        print("\n⚠️  INSTALLATION INCOMPLÈTE")
        print("\nCorrigez les erreurs ci-dessus puis relancez ce script.")
    print()


def main() -> int:
    print("=" * 70)
    print("🔍 VÉRIFICATION DE L'INSTALLATION IZVOX")
    print("=" * 70)
    results = {
        "Python 3.10+": check_python_version(),
        "Dépendances": check_dependencies(),
        "GPU (CUDA)": check_cuda(),
        "VB-Cable": check_vbcable(),
        "Modèles": check_models(),
    }
    print_summary(results)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
