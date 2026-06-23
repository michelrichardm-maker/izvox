# 🌍 izvox — Traducteur Bidirectionnel Temps Réel

> Traduction instantanée **FR ⇄ EN** pour vos visioconférences Teams, Zoom, Meet — **100 % locale**.

[![License](https://img.shields.io/github/license/michelrichardm-maker/izvox)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](#prérequis)

## ✨ Caractéristiques

- ⚡ **Latence ultra-basse** : < 600 ms (profil HIGH)
- 💰 **100 % gratuit** : aucun API cloud payant, tout en local
- 🔒 **Privé** : aucune donnée envoyée sur Internet
- 🎯 **Adaptatif** : détecte automatiquement votre GPU/CPU et ajuste les modèles
- 🎤 **Bidirectionnel** : votre voix → anglais, leur voix → français, simultanément

## 🚀 Installation rapide

```powershell
# 1. Cloner le projet
git clone https://github.com/user/izvox.git
cd izvox

# 2. Installer VB-Audio Virtual Cable (voir scripts/setup_vbcable.md)

# 3. Installer les dépendances Python
.\scripts\install_windows.bat

# 4. Lancer
.\scripts\run.bat
```

## 🧠 Architecture

```
┌─────────────────┐    ┌─────┐    ┌──────────┐    ┌────────────┐    ┌─────────┐
│ 🎤 Micro (FR)   │ →  │ VAD │ →  │ Whisper  │ →  │   NLLB     │ →  │ Piper   │ →  CABLE Input → Teams (EN)
└─────────────────┘    └─────┘    └──────────┘    └────────────┘    └─────────┘

┌─────────────────┐    ┌─────┐    ┌──────────┐    ┌────────────┐    ┌─────────┐
│ Teams → CABLE-B │ →  │ VAD │ →  │ Whisper  │ →  │   NLLB     │ →  │ Piper   │ →  🔊 Haut-parleurs (FR)
└─────────────────┘    └─────┘    └──────────┘    └────────────┘    └─────────┘
```

Détails complets : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📊 Profils de performance

| Profil              | Matériel cible            | Modèles                           | Latence  |
|---------------------|---------------------------|-----------------------------------|----------|
| `high_performance`  | RTX 3060+ (12 GB VRAM)    | Whisper large-v3 + NLLB-3.3B      | ~500 ms  |
| `balanced` (défaut) | RTX 2060/3050 (6-8 GB)    | Whisper medium + NLLB-1.3B        | ~700 ms  |
| `low_resource`      | GPU intégré (<6 GB)       | Whisper small + NLLB-600M         | ~1000 ms |
| `cpu_only`          | Pas de GPU                | Whisper tiny + Opus-MT            | ~1500 ms |

Le profil est **détecté automatiquement** au démarrage. Pour forcer :

```powershell
python -m src.main --profile high_performance
```

## 📖 Documentation

- [Installation détaillée](docs/INSTALLATION.md)
- [Guide d'utilisation](docs/USAGE.md)
- [Configuration avancée](docs/CONFIGURATION.md)
- [Architecture technique](docs/ARCHITECTURE.md)
- [Dépannage](docs/TROUBLESHOOTING.md)
- [Référence API](docs/API.md)
- [Setup VB-Cable](scripts/setup_vbcable.md)

## 📋 Prérequis

- **OS** : Windows 10/11 (64-bit)
- **Python** : 3.10 ou supérieur
- **GPU** : NVIDIA CUDA recommandé (mais CPU supporté)
- **Audio** : VB-Audio Virtual Cable (A + B) — voir [setup_vbcable.md](scripts/setup_vbcable.md)
- **Disque** : ~5 GB pour les modèles (profil balanced)

## 🛠️ Outils inclus

```powershell
python tools\setup_check.py         # Vérifie l'installation
python tools\audio_diagnostic.py    # Liste les périphériques audio
python tools\benchmark.py           # Mesure la latence de chaque étape
python tools\test_translation.py    # REPL de traduction interactif
python tools\download_models.py     # Pré-télécharge tous les modèles
```

## 🧪 Tests

```powershell
pip install pytest pytest-asyncio
pytest tests/ -v
```

## 🤝 Contribuer

Les PR sont les bienvenues. Pour les changements majeurs, ouvrez d'abord une issue.

## 📄 Licence

MIT — voir [LICENSE](LICENSE).

## 🙏 Crédits

izvox repose sur des projets open source remarquables :
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 + Whisper)
- [NLLB-200](https://ai.meta.com/research/no-language-left-behind/) (Meta)
- [Piper TTS](https://github.com/rhasspy/piper)
- [Silero VAD](https://github.com/snakers4/silero-vad)
- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) (WASAPI loopback)
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
