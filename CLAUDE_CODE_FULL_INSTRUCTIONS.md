# 🎯 INSTRUCTIONS CLAUDE CODE - Traducteur Bidirectionnel Temps Réel

## MISSION PRINCIPALE

Tu es chargé de développer **de A à Z** une solution complète, professionnelle et clé en main de traduction bidirectionnelle ultra-basse latence pour visioconférences (Teams/Zoom/Meet) sur Windows.

**Objectif final:** Livrer un projet fonctionnel, testé, documenté, que l'utilisateur peut installer et utiliser immédiatement pour ses appels professionnels avec des interlocuteurs anglophones.

---

## 📋 TABLE DES MATIÈRES

1. [Contexte et Objectifs](#1-contexte-et-objectifs)
2. [Architecture Technique](#2-architecture-technique)
3. [Stack Technologique](#3-stack-technologique)
4. [Structure du Projet](#4-structure-du-projet)
5. [Développement - Phase 1: Core Engine](#5-développement---phase-1-core-engine)
6. [Développement - Phase 2: Gestionnaire de Modèles](#6-développement---phase-2-gestionnaire-de-modèles)
7. [Développement - Phase 3: Pipeline Audio](#7-développement---phase-3-pipeline-audio)
8. [Développement - Phase 4: Intégration Complète](#8-développement---phase-4-intégration-complète)
9. [Développement - Phase 5: Outils et Utilitaires](#9-développement---phase-5-outils-et-utilitaires)
10. [Tests et Validation](#10-tests-et-validation)
11. [Documentation](#11-documentation)
12. [Livraison Finale](#12-livraison-finale)

---

## 1. CONTEXTE ET OBJECTIFS

### 1.1 Problème à Résoudre

L'utilisateur est francophone et doit régulièrement communiquer avec des fournisseurs/clients anglophones via Teams, Zoom ou Google Meet. Il a besoin d'une solution qui:

- **Traduit SA voix** (français → anglais) pour que l'interlocuteur entende de l'anglais
- **Traduit la voix de l'INTERLOCUTEUR** (anglais → français) pour qu'il comprenne
- Fonctionne en **temps réel** avec latence < 600ms
- Est **100% locale** (pas d'APIs cloud payantes)
- S'adapte **automatiquement** au matériel disponible (GPU/CPU)

### 1.2 Contraintes Techniques

| Contrainte | Exigence |
|------------|----------|
| Latence cible | < 600ms (idéal: 400-500ms) |
| Compatibilité GPU | NVIDIA CUDA, AMD/Intel DirectML, CPU only |
| OS | Windows 10/11 (64-bit) |
| Langues | Français ↔ Anglais (extensible) |
| Coût runtime | $0 (tout en local) |
| Confidentialité | 100% des données restent locales |
| Installation | Automatisée, clé en main |

### 1.3 Livrables Attendus

```
izvox/
├── src/                          # Code source principal
│   ├── __init__.py
│   ├── main.py                   # Point d'entrée
│   ├── config.py                 # Configuration centralisée
│   ├── hardware_detector.py      # Détection matérielle
│   ├── model_manager.py          # Gestion des modèles AI
│   ├── audio_manager.py          # Gestion audio (PyAudioWPatch)
│   ├── vad.py                    # Voice Activity Detection
│   ├── stt.py                    # Speech-to-Text (Faster-Whisper)
│   ├── translator.py             # Traduction (NLLB/Opus-MT)
│   ├── tts.py                    # Text-to-Speech (Piper)
│   ├── pipeline.py               # Pipeline de traduction complet
│   └── utils.py                  # Utilitaires divers
├── tests/                        # Tests unitaires et intégration
│   ├── __init__.py
│   ├── test_hardware.py
│   ├── test_audio.py
│   ├── test_stt.py
│   ├── test_translator.py
│   ├── test_tts.py
│   └── test_pipeline.py
├── tools/                        # Outils utilitaires
│   ├── setup_check.py            # Vérification installation
│   ├── audio_diagnostic.py       # Diagnostic audio
│   ├── benchmark.py              # Benchmark performance
│   └── download_models.py        # Téléchargement modèles
├── docs/                         # Documentation
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── USAGE.md
│   ├── TROUBLESHOOTING.md
│   └── ARCHITECTURE.md
├── models/                       # Modèles AI (téléchargés)
│   ├── whisper/
│   ├── nllb/
│   └── piper/
├── config/                       # Fichiers de configuration
│   ├── default.yaml
│   ├── high_performance.yaml
│   ├── balanced.yaml
│   └── low_resource.yaml
├── scripts/                      # Scripts d'installation
│   ├── install_windows.bat
│   ├── install_windows.ps1
│   └── setup_vbcable.md
├── requirements.txt              # Dépendances de base
├── requirements_cuda.txt         # Dépendances CUDA
├── requirements_directml.txt     # Dépendances DirectML
├── requirements_cpu.txt          # Dépendances CPU only
├── setup.py                      # Installation package
├── pyproject.toml                # Configuration projet
├── README.md                     # Documentation principale
├── LICENSE                       # Licence MIT
└── .gitignore
```

---

## 2. ARCHITECTURE TECHNIQUE

### 2.1 Vue d'Ensemble des Flux Audio

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        ARCHITECTURE BIDIRECTIONNELLE                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                     FLUX OUTGOING (Vous → Interlocuteur)                │ ║
║  │                                                                         │ ║
║  │  🎤 Micro Physique                                                      │ ║
║  │       │                                                                 │ ║
║  │       ▼                                                                 │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ PyAudio     │ ← Capture audio brut (16kHz, mono, 16-bit)            │ ║
║  │  │ WASAPI      │                                                        │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ Silero VAD  │ ← Détection activité vocale (évite traductions vides) │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (audio si parole détectée)                                    │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ Faster-     │ ← STT: Audio FR → Texte FR                            │ ║
║  │  │ Whisper     │   Modèle adapté selon GPU (large-v3/medium/small)     │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (texte français)                                              │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ NLLB-200    │ ← Traduction: Texte FR → Texte EN                     │ ║
║  │  │ (Meta)      │   Modèle adapté selon GPU (3.3B/1.3B/600M)            │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (texte anglais)                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ Piper TTS   │ ← TTS: Texte EN → Audio EN                            │ ║
║  │  │ (ONNX)      │   Voix anglaise naturelle                             │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (audio anglais)                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ VB-Cable    │ ← Sortie vers câble virtuel                           │ ║
║  │  │ Input 1     │                                                        │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  💻 Teams/Zoom (configuré pour utiliser VB-Cable comme micro)          │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  🌐 Interlocuteur entend de l'ANGLAIS                                   │ ║
║  │                                                                         │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                     FLUX INCOMING (Interlocuteur → Vous)                │ ║
║  │                                                                         │ ║
║  │  🌐 Interlocuteur parle en ANGLAIS                                      │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  💻 Teams/Zoom (configuré pour sortir audio sur VB-Cable B)            │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ VB-Cable B  │ ← Loopback WASAPI                                     │ ║
║  │  │ Output      │                                                        │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ PyAudio     │ ← Capture loopback (WASAPI exclusif)                  │ ║
║  │  │ WASAPI      │                                                        │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ Silero VAD  │ ← Détection activité vocale                           │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ Faster-     │ ← STT: Audio EN → Texte EN                            │ ║
║  │  │ Whisper     │                                                        │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (texte anglais)                                               │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ NLLB-200    │ ← Traduction: Texte EN → Texte FR                     │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (texte français)                                              │ ║
║  │         ▼                                                               │ ║
║  │  ┌─────────────┐                                                        │ ║
║  │  │ Piper TTS   │ ← TTS: Texte FR → Audio FR                            │ ║
║  │  │ (ONNX)      │   Voix française naturelle                            │ ║
║  │  └──────┬──────┘                                                        │ ║
║  │         │ (audio français)                                              │ ║
║  │         ▼                                                               │ ║
║  │  🔊 Haut-parleurs/Casque (périphérique par défaut Windows)             │ ║
║  │         │                                                               │ ║
║  │         ▼                                                               │ ║
║  │  👤 Vous entendez du FRANÇAIS                                           │ ║
║  │                                                                         │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 2.2 Diagramme de Classes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DIAGRAMME DE CLASSES                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐
│   HardwareDetector  │       │     ModelManager    │
├─────────────────────┤       ├─────────────────────┤
│ - has_cuda: bool    │       │ - models_dir: Path  │
│ - has_directml: bool│       │ - profile: dict     │
│ - gpu_name: str     │       │ - hardware: Hardware│
│ - vram_mb: int      │       ├─────────────────────┤
│ - level: HWLevel    │       │ + detect_hardware() │
├─────────────────────┤       │ + select_profile()  │
│ + detect()          │       │ + download_models() │
│ + get_optimal_cfg() │       │ + load_models()     │
└─────────────────────┘       └─────────────────────┘
          │                             │
          └──────────────┬──────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TranslationPipeline                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ - direction: str ("outgoing" | "incoming")                                  │
│ - audio_config: AudioConfig                                                 │
│ - vad: VADProcessor                                                         │
│ - stt: STTProcessor                                                         │
│ - translator: TranslatorProcessor                                           │
│ - tts: TTSProcessor                                                         │
│ - audio_input: AudioInputStream                                             │
│ - audio_output: AudioOutputStream                                           │
│ - is_running: bool                                                          │
│ - stats: PipelineStats                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ + async initialize()                                                        │
│ + async run()                                                               │
│ + async process_audio_chunk(chunk: bytes) -> Optional[bytes]                │
│ + async cleanup()                                                           │
│ + get_stats() -> dict                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          │ uses
          ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  VADProcessor │  │ STTProcessor  │  │  Translator   │  │ TTSProcessor  │
├───────────────┤  ├───────────────┤  ├───────────────┤  ├───────────────┤
│ - model       │  │ - model       │  │ - model       │  │ - model       │
│ - threshold   │  │ - language    │  │ - src_lang    │  │ - voice       │
│ - sample_rate │  │ - device      │  │ - tgt_lang    │  │ - sample_rate │
├───────────────┤  ├───────────────┤  ├───────────────┤  ├───────────────┤
│ + is_speech() │  │ + transcribe()│  │ + translate() │  │ + synthesize()│
│ + reset()     │  │ + add_audio() │  │ + set_langs() │  │ + stream()    │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              AudioManager                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ - pyaudio: PyAudio                                                          │
│ - devices: List[DeviceInfo]                                                 │
│ - streams: Dict[str, Stream]                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ + list_devices() -> List[DeviceInfo]                                        │
│ + find_device(pattern: str) -> DeviceInfo                                   │
│ + find_loopback(pattern: str) -> DeviceInfo                                 │
│ + open_input_stream(device_id: int, config: AudioConfig) -> Stream          │
│ + open_output_stream(device_id: int, config: AudioConfig) -> Stream         │
│ + close_all()                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           BilingualTranslator                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ - outgoing_pipeline: TranslationPipeline                                    │
│ - incoming_pipeline: TranslationPipeline                                    │
│ - config: AppConfig                                                         │
│ - is_running: bool                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ + async start()                                                             │
│ + async stop()                                                              │
│ + get_status() -> dict                                                      │
│ + get_stats() -> dict                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. STACK TECHNOLOGIQUE

### 3.1 Composants Principaux

| Composant | Technologie | Version | Rôle |
|-----------|-------------|---------|------|
| **STT** | Faster-Whisper | ≥1.0.0 | Speech-to-Text (Whisper optimisé) |
| **Traduction** | NLLB-200 (Meta) | via transformers | Traduction multilingue |
| **Traduction (fallback)** | Opus-MT | via transformers | Pour CPU faible |
| **TTS** | Piper | ≥1.2.0 | Text-to-Speech (ONNX) |
| **VAD** | Silero VAD | via torch.hub | Détection voix |
| **Audio** | PyAudioWPatch | ≥0.2.12 | Capture/Lecture WASAPI |
| **Deep Learning** | PyTorch | ≥2.0.0 | Framework ML |
| **GPU Inference** | ONNX Runtime | ≥1.16.0 | Exécution optimisée |

### 3.2 Profils de Performance

```yaml
# Profil HIGH (RTX 3060+ 12GB VRAM)
high_performance:
  stt:
    model: "large-v3"
    device: "cuda"
    compute_type: "float16"
  translation:
    model: "facebook/nllb-200-3.3B"
    device: "cuda"
  tts:
    quality: "high"
  vad:
    backend: "silero"
  audio:
    chunk_size: 1024
    sample_rate: 16000
  expected_latency_ms: 500

# Profil MEDIUM (RTX 2060/3050 6-8GB VRAM)
balanced:
  stt:
    model: "medium"
    device: "cuda"
    compute_type: "int8"
  translation:
    model: "facebook/nllb-200-1.3B"
    device: "cuda"
  tts:
    quality: "medium"
  vad:
    backend: "silero"
  audio:
    chunk_size: 1024
    sample_rate: 16000
  expected_latency_ms: 700

# Profil LOW (GPU intégré ou ancien)
low_resource:
  stt:
    model: "small"
    device: "cuda"  # ou "cpu"
    compute_type: "int8"
  translation:
    model: "facebook/nllb-200-distilled-600M"
    device: "cuda"  # ou "cpu"
  tts:
    quality: "low"
  vad:
    backend: "silero"
  audio:
    chunk_size: 2048
    sample_rate: 16000
  expected_latency_ms: 1000

# Profil CPU_ONLY (pas de GPU)
cpu_only:
  stt:
    model: "tiny"
    device: "cpu"
    compute_type: "int8"
  translation:
    model: "Helsinki-NLP/opus-mt-fr-en"  # Plus léger
    device: "cpu"
  tts:
    quality: "low"
  vad:
    backend: "rms"  # VAD simple basé sur RMS
  audio:
    chunk_size: 2048
    sample_rate: 16000
  expected_latency_ms: 1500
```

---

## 4. STRUCTURE DU PROJET

### 4.1 Arborescence Détaillée

Crée la structure suivante avec tous les fichiers:

```
izvox/
│
├── src/
│   ├── __init__.py
│   │   """
│   │   Package principal du traducteur bidirectionnel.
│   │   """
│   │   __version__ = "2.0.0"
│   │   __author__ = "Expert Python AI"
│   │
│   ├── main.py                    # Point d'entrée principal
│   ├── config.py                  # Classes de configuration
│   ├── hardware_detector.py       # Détection GPU/CPU
│   ├── model_manager.py           # Téléchargement/chargement modèles
│   ├── audio_manager.py           # Gestion PyAudio/WASAPI
│   ├── vad.py                     # Voice Activity Detection
│   ├── stt.py                     # Speech-to-Text
│   ├── translator.py              # Traduction NLLB/Opus-MT
│   ├── tts.py                     # Text-to-Speech Piper
│   ├── pipeline.py                # Pipeline complet
│   ├── exceptions.py              # Exceptions personnalisées
│   └── utils.py                   # Utilitaires
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures pytest
│   ├── test_hardware.py
│   ├── test_audio.py
│   ├── test_stt.py
│   ├── test_translator.py
│   ├── test_tts.py
│   ├── test_pipeline.py
│   └── test_integration.py
│
├── tools/
│   ├── setup_check.py             # Vérification complète installation
│   ├── audio_diagnostic.py        # Liste et teste périphériques
│   ├── benchmark.py               # Benchmark latence/qualité
│   ├── download_models.py         # Téléchargement manuel modèles
│   └── test_translation.py        # Test rapide FR↔EN
│
├── docs/
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── USAGE.md
│   ├── TROUBLESHOOTING.md
│   ├── ARCHITECTURE.md
│   └── API.md
│
├── config/
│   ├── default.yaml
│   ├── high_performance.yaml
│   ├── balanced.yaml
│   ├── low_resource.yaml
│   └── cpu_only.yaml
│
├── scripts/
│   ├── install_windows.bat
│   ├── install_windows.ps1
│   ├── run.bat
│   ├── run.ps1
│   └── setup_vbcable.md
│
├── models/                        # Créé automatiquement
│   └── .gitkeep
│
├── logs/                          # Créé automatiquement
│   └── .gitkeep
│
├── requirements.txt               # Dépendances communes
├── requirements_cuda.txt          # + CUDA
├── requirements_directml.txt      # + DirectML
├── requirements_cpu.txt           # CPU only
├── setup.py
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```
## 5. DÉVELOPPEMENT - PHASE 1: CORE ENGINE

### 5.1 Fichier: `src/config.py`

```python
"""
Configuration centralisée du traducteur.
Gère les paramètres audio, modèles, et profils de performance.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class HardwareLevel(Enum):
    """Niveau de performance matérielle détecté"""
    HIGH = "high"           # RTX 3060+ (12GB+ VRAM)
    MEDIUM = "medium"       # RTX 2060, 3050 (6-8GB VRAM)
    LOW = "low"             # GPU intégré ou ancien
    CPU_ONLY = "cpu_only"   # Pas de GPU dédié


class FlowDirection(Enum):
    """Direction du flux de traduction"""
    OUTGOING = "outgoing"   # Utilisateur → Interlocuteur (FR→EN)
    INCOMING = "incoming"   # Interlocuteur → Utilisateur (EN→FR)


@dataclass
class AudioConfig:
    """Configuration audio"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024          # Samples par chunk (~64ms à 16kHz)
    format: str = "int16"           # Format audio
    vad_threshold: float = 0.015    # Seuil VAD
    silence_duration: float = 0.5   # Secondes de silence avant fin de phrase
    
    # Périphériques (noms partiels pour recherche)
    input_device_pattern: str = ""          # Vide = défaut
    output_device_pattern: str = ""         # Vide = défaut
    vbcable_input_pattern: str = "CABLE Input"
    vbcable_output_pattern: str = "CABLE-B"


@dataclass
class STTConfig:
    """Configuration Speech-to-Text (Faster-Whisper)"""
    model_size: str = "medium"      # tiny, base, small, medium, large-v3
    device: str = "cuda"            # cuda, cpu
    compute_type: str = "float16"   # float16, int8, float32
    language: str = "fr"            # Langue source
    beam_size: int = 5
    vad_filter: bool = True
    download_root: str = "./models/whisper"


@dataclass
class TranslationConfig:
    """Configuration Traduction (NLLB/Opus-MT)"""
    model_name: str = "facebook/nllb-200-1.3B"
    device: str = "cuda"
    source_lang: str = "fra_Latn"   # Code NLLB pour français
    target_lang: str = "eng_Latn"   # Code NLLB pour anglais
    max_length: int = 512
    num_beams: int = 5
    cache_dir: str = "./models/nllb"


@dataclass
class TTSConfig:
    """Configuration Text-to-Speech (Piper)"""
    model_path: str = "./models/piper"
    voice_fr: str = "fr_FR-upmc-medium"
    voice_en: str = "en_US-lessac-medium"
    sample_rate: int = 22050        # Piper output rate
    speaker_id: Optional[int] = None


@dataclass
class VADConfig:
    """Configuration Voice Activity Detection"""
    backend: str = "silero"         # silero ou rms
    threshold: float = 0.5          # Pour Silero (probabilité)
    rms_threshold: float = 0.015    # Pour RMS
    min_speech_duration: float = 0.1
    min_silence_duration: float = 0.5
    sample_rate: int = 16000


@dataclass
class AppConfig:
    """Configuration globale de l'application"""
    # Profil de performance
    profile: str = "balanced"
    hardware_level: HardwareLevel = HardwareLevel.MEDIUM
    
    # Sous-configurations
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    
    # Chemins
    models_dir: Path = Path("./models")
    logs_dir: Path = Path("./logs")
    config_dir: Path = Path("./config")
    
    # Options
    verbose: bool = False
    log_level: str = "INFO"
    enable_stats: bool = True
    
    @classmethod
    def from_yaml(cls, filepath: str) -> "AppConfig":
        """Charge la configuration depuis un fichier YAML"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Construit la config depuis un dictionnaire"""
        # Implémentation de la désérialisation
        # ...
        pass
    
    def to_yaml(self, filepath: str):
        """Sauvegarde la configuration dans un fichier YAML"""
        # Implémentation de la sérialisation
        # ...
        pass
    
    def apply_profile(self, profile_name: str):
        """Applique un profil de performance prédéfini"""
        profiles = {
            "high_performance": self._profile_high,
            "balanced": self._profile_balanced,
            "low_resource": self._profile_low,
            "cpu_only": self._profile_cpu
        }
        if profile_name in profiles:
            profiles[profile_name]()
    
    def _profile_high(self):
        """Configuration haute performance"""
        self.stt.model_size = "large-v3"
        self.stt.compute_type = "float16"
        self.translation.model_name = "facebook/nllb-200-3.3B"
        self.audio.chunk_size = 1024
    
    def _profile_balanced(self):
        """Configuration équilibrée"""
        self.stt.model_size = "medium"
        self.stt.compute_type = "int8"
        self.translation.model_name = "facebook/nllb-200-1.3B"
        self.audio.chunk_size = 1024
    
    def _profile_low(self):
        """Configuration économe en ressources"""
        self.stt.model_size = "small"
        self.stt.compute_type = "int8"
        self.translation.model_name = "facebook/nllb-200-distilled-600M"
        self.audio.chunk_size = 2048
    
    def _profile_cpu(self):
        """Configuration CPU uniquement"""
        self.stt.model_size = "tiny"
        self.stt.device = "cpu"
        self.stt.compute_type = "int8"
        self.translation.model_name = "Helsinki-NLP/opus-mt-fr-en"
        self.translation.device = "cpu"
        self.vad.backend = "rms"
        self.audio.chunk_size = 2048
```

### 5.2 Fichier: `src/exceptions.py`

```python
"""
Exceptions personnalisées pour le traducteur.
"""


class TranslatorError(Exception):
    """Exception de base pour le traducteur"""
    pass


class HardwareError(TranslatorError):
    """Erreur liée au matériel (GPU, audio, etc.)"""
    pass


class ModelError(TranslatorError):
    """Erreur liée aux modèles AI"""
    pass


class ModelNotFoundError(ModelError):
    """Modèle non trouvé ou non téléchargé"""
    pass


class ModelLoadError(ModelError):
    """Erreur lors du chargement d'un modèle"""
    pass


class AudioError(TranslatorError):
    """Erreur liée à l'audio"""
    pass


class AudioDeviceNotFoundError(AudioError):
    """Périphérique audio non trouvé"""
    pass


class AudioStreamError(AudioError):
    """Erreur de stream audio"""
    pass


class PipelineError(TranslatorError):
    """Erreur dans le pipeline de traduction"""
    pass


class ConfigurationError(TranslatorError):
    """Erreur de configuration"""
    pass
```

---

## 6. DÉVELOPPEMENT - PHASE 2: GESTIONNAIRE DE MODÈLES

### 6.1 Fichier: `src/hardware_detector.py`

```python
"""
Détection automatique des capacités matérielles.
Détermine le meilleur profil de configuration selon le GPU/CPU disponible.
"""

import os
import platform
import logging
from dataclasses import dataclass
from typing import Optional

from .config import HardwareLevel


@dataclass
class HardwareInfo:
    """Informations détaillées sur le matériel"""
    # GPU
    has_cuda: bool = False
    has_directml: bool = False
    gpu_name: str = "None"
    vram_mb: int = 0
    cuda_version: Optional[str] = None
    
    # CPU
    cpu_name: str = ""
    cpu_cores: int = 1
    cpu_threads: int = 1
    
    # RAM
    ram_gb: float = 0.0
    
    # Niveau déterminé
    level: HardwareLevel = HardwareLevel.CPU_ONLY
    
    # Device recommandé
    recommended_device: str = "cpu"


class HardwareDetector:
    """
    Détecte les capacités matérielles du système.
    
    Usage:
        detector = HardwareDetector()
        hw_info = detector.detect()
        print(f"GPU: {hw_info.gpu_name}")
        print(f"Niveau recommandé: {hw_info.level}")
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect(self) -> HardwareInfo:
        """
        Effectue la détection complète du matériel.
        
        Returns:
            HardwareInfo: Informations détaillées sur le matériel
        """
        info = HardwareInfo()
        
        # Détection CPU
        self._detect_cpu(info)
        
        # Détection RAM
        self._detect_ram(info)
        
        # Détection GPU CUDA (NVIDIA)
        self._detect_cuda(info)
        
        # Détection DirectML (AMD/Intel sur Windows)
        if not info.has_cuda and platform.system() == "Windows":
            self._detect_directml(info)
        
        # Détermination du niveau de performance
        self._determine_level(info)
        
        return info
    
    def _detect_cpu(self, info: HardwareInfo):
        """Détecte les informations CPU"""
        info.cpu_cores = os.cpu_count() or 1
        info.cpu_threads = info.cpu_cores  # Simplification
        
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
            info.cpu_name = cpu_info.get('brand_raw', 'Unknown CPU')
        except ImportError:
            info.cpu_name = platform.processor() or "Unknown CPU"
    
    def _detect_ram(self, info: HardwareInfo):
        """Détecte la quantité de RAM"""
        try:
            import psutil
            info.ram_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            info.ram_gb = 8.0  # Estimation par défaut
    
    def _detect_cuda(self, info: HardwareInfo):
        """Détecte GPU NVIDIA via CUDA"""
        try:
            import torch
            
            if torch.cuda.is_available():
                info.has_cuda = True
                info.gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                info.vram_mb = props.total_memory // (1024 * 1024)
                info.cuda_version = torch.version.cuda
                info.recommended_device = "cuda"
                
                self.logger.info(f"CUDA détecté: {info.gpu_name} ({info.vram_mb}MB)")
                
        except ImportError:
            self.logger.debug("PyTorch non installé, détection CUDA ignorée")
        except Exception as e:
            self.logger.warning(f"Erreur détection CUDA: {e}")
    
    def _detect_directml(self, info: HardwareInfo):
        """Détecte support DirectML (Windows AMD/Intel)"""
        try:
            import torch_directml
            
            info.has_directml = True
            info.gpu_name = "DirectML Compatible GPU"
            info.vram_mb = 4096  # Estimation conservative
            info.recommended_device = "privateuseone"  # Device DirectML
            
            self.logger.info("DirectML détecté")
            
        except ImportError:
            self.logger.debug("torch-directml non installé")
    
    def _determine_level(self, info: HardwareInfo):
        """Détermine le niveau de performance recommandé"""
        if info.has_cuda:
            if info.vram_mb >= 12000:
                info.level = HardwareLevel.HIGH
            elif info.vram_mb >= 6000:
                info.level = HardwareLevel.MEDIUM
            else:
                info.level = HardwareLevel.LOW
        elif info.has_directml:
            info.level = HardwareLevel.MEDIUM
        else:
            info.level = HardwareLevel.CPU_ONLY
            info.recommended_device = "cpu"
    
    def print_info(self, info: HardwareInfo):
        """Affiche les informations matérielles de manière formatée"""
        print("\n" + "=" * 70)
        print("🖥️  DÉTECTION MATÉRIELLE")
        print("=" * 70)
        print(f"CPU: {info.cpu_name}")
        print(f"Cores/Threads: {info.cpu_cores}/{info.cpu_threads}")
        print(f"RAM: {info.ram_gb:.1f} GB")
        print()
        print(f"GPU: {info.gpu_name}")
        print(f"VRAM: {info.vram_mb} MB")
        print(f"CUDA: {'✓ ' + (info.cuda_version or '') if info.has_cuda else '✗'}")
        print(f"DirectML: {'✓' if info.has_directml else '✗'}")
        print()
        print(f"🎯 Niveau recommandé: {info.level.value.upper()}")
        print(f"📍 Device: {info.recommended_device}")
        print("=" * 70)
```

### 6.2 Fichier: `src/model_manager.py`

```python
"""
Gestionnaire de modèles AI.
Télécharge, cache et charge les modèles selon le profil détecté.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .config import AppConfig, HardwareLevel
from .hardware_detector import HardwareDetector, HardwareInfo
from .exceptions import ModelNotFoundError, ModelLoadError


@dataclass
class ModelPaths:
    """Chemins vers les modèles chargés"""
    whisper: Optional[str] = None
    nllb: Optional[str] = None
    piper_fr: Optional[Path] = None
    piper_en: Optional[Path] = None
    silero_vad: Optional[Any] = None


class ModelManager:
    """
    Gère le téléchargement et le chargement des modèles AI.
    
    Usage:
        manager = ModelManager(config)
        manager.initialize()
        models = manager.get_models()
    """
    
    # Mapping des profils vers les modèles
    PROFILES = {
        HardwareLevel.HIGH: {
            "stt_model": "large-v3",
            "stt_compute_type": "float16",
            "translation_model": "facebook/nllb-200-3.3B",
            "tts_quality": "high",
            "vad_backend": "silero"
        },
        HardwareLevel.MEDIUM: {
            "stt_model": "medium",
            "stt_compute_type": "int8",
            "translation_model": "facebook/nllb-200-1.3B",
            "tts_quality": "medium",
            "vad_backend": "silero"
        },
        HardwareLevel.LOW: {
            "stt_model": "small",
            "stt_compute_type": "int8",
            "translation_model": "facebook/nllb-200-distilled-600M",
            "tts_quality": "low",
            "vad_backend": "silero"
        },
        HardwareLevel.CPU_ONLY: {
            "stt_model": "tiny",
            "stt_compute_type": "int8",
            "translation_model": "Helsinki-NLP/opus-mt-fr-en",
            "tts_quality": "low",
            "vad_backend": "rms"
        }
    }
    
    # URLs et infos des modèles Piper
    PIPER_VOICES = {
        "fr_FR-upmc-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/",
            "files": ["fr_FR-upmc-medium.onnx", "fr_FR-upmc-medium.onnx.json"]
        },
        "en_US-lessac-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/",
            "files": ["en_US-lessac-medium.onnx", "en_US-lessac-medium.onnx.json"]
        }
    }
    
    def __init__(self, config: AppConfig, auto_detect: bool = True):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.models_dir = Path(config.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.hardware_info: Optional[HardwareInfo] = None
        self.profile: Optional[Dict] = None
        self.model_paths = ModelPaths()
        
        if auto_detect:
            self._detect_and_configure()
    
    def _detect_and_configure(self):
        """Détecte le matériel et configure automatiquement"""
        detector = HardwareDetector()
        self.hardware_info = detector.detect()
        self.profile = self.PROFILES[self.hardware_info.level]
        
        # Mise à jour de la configuration
        self._apply_profile_to_config()
    
    def _apply_profile_to_config(self):
        """Applique le profil détecté à la configuration"""
        if not self.profile:
            return
        
        # STT
        self.config.stt.model_size = self.profile["stt_model"]
        self.config.stt.compute_type = self.profile["stt_compute_type"]
        self.config.stt.device = self.hardware_info.recommended_device
        
        # Translation
        self.config.translation.model_name = self.profile["translation_model"]
        self.config.translation.device = self.hardware_info.recommended_device
        
        # VAD
        self.config.vad.backend = self.profile["vad_backend"]
    
    def initialize(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Initialise le gestionnaire et vérifie/télécharge les modèles.
        
        Args:
            verbose: Afficher les informations de progression
            
        Returns:
            Dict avec les informations sur les modèles configurés
        """
        if verbose and self.hardware_info:
            HardwareDetector().print_info(self.hardware_info)
            self._print_profile()
        
        # Vérification/téléchargement des modèles
        self._setup_whisper()
        self._setup_translation()
        self._setup_piper()
        self._setup_vad()
        
        return {
            "hardware": self.hardware_info,
            "profile": self.profile,
            "models": self.model_paths
        }
    
    def _print_profile(self):
        """Affiche le profil sélectionné"""
        if not self.profile or not self.hardware_info:
            return
        
        print(f"\n📊 PROFIL: {self.hardware_info.level.value.upper()}")
        print("=" * 70)
        print(f"STT: Whisper {self.profile['stt_model']} ({self.profile['stt_compute_type']})")
        print(f"Traduction: {self.profile['translation_model']}")
        print(f"TTS: Piper {self.profile['tts_quality']}")
        print(f"VAD: {self.profile['vad_backend']}")
        print("=" * 70)
    
    def _setup_whisper(self):
        """Configure Faster-Whisper (téléchargement auto)"""
        self.logger.info(f"Configuration Whisper: {self.config.stt.model_size}")
        # Faster-Whisper télécharge automatiquement au premier usage
        self.model_paths.whisper = self.config.stt.model_size
    
    def _setup_translation(self):
        """Configure le modèle de traduction"""
        self.logger.info(f"Configuration traduction: {self.config.translation.model_name}")
        # Transformers télécharge automatiquement
        self.model_paths.nllb = self.config.translation.model_name
    
    def _setup_piper(self):
        """Configure et télécharge les voix Piper si nécessaire"""
        piper_dir = self.models_dir / "piper"
        piper_dir.mkdir(exist_ok=True)
        
        for voice_name in [self.config.tts.voice_fr, self.config.tts.voice_en]:
            voice_dir = piper_dir / voice_name
            
            if not self._check_piper_voice(voice_dir, voice_name):
                self._download_piper_voice(voice_name, voice_dir)
        
        self.model_paths.piper_fr = piper_dir / self.config.tts.voice_fr
        self.model_paths.piper_en = piper_dir / self.config.tts.voice_en
    
    def _check_piper_voice(self, voice_dir: Path, voice_name: str) -> bool:
        """Vérifie si une voix Piper est déjà téléchargée"""
        if voice_name not in self.PIPER_VOICES:
            return False
        
        for filename in self.PIPER_VOICES[voice_name]["files"]:
            if not (voice_dir / filename).exists():
                return False
        return True
    
    def _download_piper_voice(self, voice_name: str, voice_dir: Path):
        """Télécharge une voix Piper"""
        import urllib.request
        
        if voice_name not in self.PIPER_VOICES:
            self.logger.warning(f"Voix inconnue: {voice_name}")
            return
        
        voice_info = self.PIPER_VOICES[voice_name]
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Téléchargement voix Piper: {voice_name}")
        
        for filename in voice_info["files"]:
            url = voice_info["url"] + filename
            filepath = voice_dir / filename
            
            if not filepath.exists():
                self.logger.info(f"  Téléchargement: {filename}")
                urllib.request.urlretrieve(url, filepath)
    
    def _setup_vad(self):
        """Configure le VAD"""
        if self.config.vad.backend == "silero":
            self.logger.info("Configuration Silero VAD")
            # Silero se charge via torch.hub automatiquement
        else:
            self.logger.info("Configuration VAD RMS (simple)")
    
    def get_config(self) -> AppConfig:
        """Retourne la configuration mise à jour"""
        return self.config
    
    def get_recommended_audio_config(self) -> Dict[str, Any]:
        """Retourne la configuration audio recommandée"""
        chunk_sizes = {
            HardwareLevel.HIGH: 1024,
            HardwareLevel.MEDIUM: 1024,
            HardwareLevel.LOW: 2048,
            HardwareLevel.CPU_ONLY: 2048
        }
        
        level = self.hardware_info.level if self.hardware_info else HardwareLevel.CPU_ONLY
        
        return {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": chunk_sizes[level],
            "format": "int16"
        }
```

---

## 7. DÉVELOPPEMENT - PHASE 3: PIPELINE AUDIO

### 7.1 Fichier: `src/audio_manager.py`

```python
"""
Gestionnaire audio avec support WASAPI (Windows).
Gère la capture microphone, loopback, et sortie vers VB-Cable.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import pyaudiowpatch as pyaudio
import numpy as np

from .config import AudioConfig
from .exceptions import AudioDeviceNotFoundError, AudioStreamError


@dataclass
class DeviceInfo:
    """Information sur un périphérique audio"""
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    is_input: bool
    is_output: bool
    is_loopback: bool = False
    host_api: int = 0


class AudioManager:
    """
    Gestionnaire centralisé des périphériques et streams audio.
    Utilise PyAudioWPatch pour le support WASAPI loopback.
    
    Usage:
        manager = AudioManager()
        devices = manager.list_devices()
        
        # Ouvrir un stream d'entrée (microphone)
        input_stream = manager.open_input_stream(
            device_pattern="Microphone",
            config=audio_config
        )
        
        # Ouvrir un stream loopback (capture audio système)
        loopback_stream = manager.open_loopback_stream(
            device_pattern="CABLE-B",
            config=audio_config
        )
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._streams: Dict[str, pyaudio.Stream] = {}
        self._devices: List[DeviceInfo] = []
    
    @property
    def pyaudio(self) -> pyaudio.PyAudio:
        """Accès lazy à l'instance PyAudio"""
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
            self._scan_devices()
        return self._pyaudio
    
    def _scan_devices(self):
        """Scanne tous les périphériques audio disponibles"""
        self._devices = []
        
        for i in range(self.pyaudio.get_device_count()):
            try:
                info = self.pyaudio.get_device_info_by_index(i)
                
                device = DeviceInfo(
                    index=i,
                    name=info['name'],
                    max_input_channels=info['maxInputChannels'],
                    max_output_channels=info['maxOutputChannels'],
                    default_sample_rate=info['defaultSampleRate'],
                    is_input=info['maxInputChannels'] > 0,
                    is_output=info['maxOutputChannels'] > 0,
                    is_loopback='loopback' in info['name'].lower(),
                    host_api=info['hostApi']
                )
                
                self._devices.append(device)
                
            except Exception as e:
                self.logger.warning(f"Erreur lecture device {i}: {e}")
    
    def list_devices(self, input_only: bool = False, output_only: bool = False) -> List[DeviceInfo]:
        """
        Liste les périphériques audio disponibles.
        
        Args:
            input_only: Ne retourner que les périphériques d'entrée
            output_only: Ne retourner que les périphériques de sortie
            
        Returns:
            Liste des périphériques
        """
        _ = self.pyaudio  # Force l'initialisation
        
        devices = self._devices
        
        if input_only:
            devices = [d for d in devices if d.is_input]
        elif output_only:
            devices = [d for d in devices if d.is_output]
        
        return devices
    
    def find_device(self, pattern: str, input_only: bool = False, 
                    output_only: bool = False) -> DeviceInfo:
        """
        Trouve un périphérique par motif de nom.
        
        Args:
            pattern: Motif à rechercher (insensible à la casse)
            input_only: Rechercher uniquement parmi les entrées
            output_only: Rechercher uniquement parmi les sorties
            
        Returns:
            DeviceInfo du périphérique trouvé
            
        Raises:
            AudioDeviceNotFoundError: Si aucun périphérique ne correspond
        """
        devices = self.list_devices(input_only=input_only, output_only=output_only)
        pattern_lower = pattern.lower()
        
        for device in devices:
            if pattern_lower in device.name.lower():
                return device
        
        raise AudioDeviceNotFoundError(
            f"Périphérique '{pattern}' non trouvé. "
            f"Disponibles: {[d.name for d in devices]}"
        )
    
    def find_loopback_device(self, pattern: str) -> DeviceInfo:
        """
        Trouve un périphérique loopback WASAPI.
        
        Args:
            pattern: Motif à rechercher
            
        Returns:
            DeviceInfo du périphérique loopback
        """
        try:
            # Recherche dans les périphériques WASAPI
            wasapi_info = self.pyaudio.get_host_api_info_by_type(pyaudio.paWASAPI)
            
            for i in range(wasapi_info['deviceCount']):
                device_info = self.pyaudio.get_device_info_by_host_api_device_index(
                    wasapi_info['index'], i
                )
                
                if (pattern.lower() in device_info['name'].lower() and
                    device_info['maxInputChannels'] > 0):
                    
                    return DeviceInfo(
                        index=device_info['index'],
                        name=device_info['name'],
                        max_input_channels=device_info['maxInputChannels'],
                        max_output_channels=device_info['maxOutputChannels'],
                        default_sample_rate=device_info['defaultSampleRate'],
                        is_input=True,
                        is_output=False,
                        is_loopback=True,
                        host_api=wasapi_info['index']
                    )
            
            raise AudioDeviceNotFoundError(f"Loopback '{pattern}' non trouvé")
            
        except Exception as e:
            raise AudioDeviceNotFoundError(f"Erreur recherche loopback: {e}")
    
    def get_default_input_device(self) -> DeviceInfo:
        """Retourne le périphérique d'entrée par défaut"""
        try:
            info = self.pyaudio.get_default_input_device_info()
            return self._info_to_device(info)
        except Exception as e:
            raise AudioDeviceNotFoundError(f"Pas de périphérique d'entrée par défaut: {e}")
    
    def get_default_output_device(self) -> DeviceInfo:
        """Retourne le périphérique de sortie par défaut"""
        try:
            info = self.pyaudio.get_default_output_device_info()
            return self._info_to_device(info)
        except Exception as e:
            raise AudioDeviceNotFoundError(f"Pas de périphérique de sortie par défaut: {e}")
    
    def _info_to_device(self, info: Dict) -> DeviceInfo:
        """Convertit un dict PyAudio en DeviceInfo"""
        return DeviceInfo(
            index=info['index'],
            name=info['name'],
            max_input_channels=info['maxInputChannels'],
            max_output_channels=info['maxOutputChannels'],
            default_sample_rate=info['defaultSampleRate'],
            is_input=info['maxInputChannels'] > 0,
            is_output=info['maxOutputChannels'] > 0,
            host_api=info['hostApi']
        )
    
    def open_input_stream(self, config: AudioConfig, 
                          device: Optional[DeviceInfo] = None,
                          device_pattern: Optional[str] = None,
                          stream_id: str = "input") -> pyaudio.Stream:
        """
        Ouvre un stream d'entrée audio.
        
        Args:
            config: Configuration audio
            device: Périphérique à utiliser (prioritaire)
            device_pattern: Motif pour trouver le périphérique
            stream_id: Identifiant unique du stream
            
        Returns:
            Stream PyAudio ouvert
        """
        if device is None:
            if device_pattern:
                device = self.find_device(device_pattern, input_only=True)
            else:
                device = self.get_default_input_device()
        
        try:
            stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=config.chunk_size
            )
            
            self._streams[stream_id] = stream
            self.logger.info(f"Stream input ouvert: {device.name}")
            
            return stream
            
        except Exception as e:
            raise AudioStreamError(f"Erreur ouverture stream input: {e}")
    
    def open_output_stream(self, config: AudioConfig,
                           device: Optional[DeviceInfo] = None,
                           device_pattern: Optional[str] = None,
                           stream_id: str = "output") -> pyaudio.Stream:
        """
        Ouvre un stream de sortie audio.
        
        Args:
            config: Configuration audio
            device: Périphérique à utiliser
            device_pattern: Motif pour trouver le périphérique
            stream_id: Identifiant unique du stream
            
        Returns:
            Stream PyAudio ouvert
        """
        if device is None:
            if device_pattern:
                device = self.find_device(device_pattern, output_only=True)
            else:
                device = self.get_default_output_device()
        
        try:
            stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                output=True,
                output_device_index=device.index,
                frames_per_buffer=config.chunk_size
            )
            
            self._streams[stream_id] = stream
            self.logger.info(f"Stream output ouvert: {device.name}")
            
            return stream
            
        except Exception as e:
            raise AudioStreamError(f"Erreur ouverture stream output: {e}")
    
    def open_loopback_stream(self, config: AudioConfig,
                             device_pattern: str,
                             stream_id: str = "loopback") -> pyaudio.Stream:
        """
        Ouvre un stream loopback WASAPI.
        
        Args:
            config: Configuration audio
            device_pattern: Motif pour trouver le périphérique loopback
            stream_id: Identifiant unique du stream
            
        Returns:
            Stream PyAudio en mode loopback
        """
        device = self.find_loopback_device(device_pattern)
        
        try:
            stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=config.chunk_size
            )
            
            self._streams[stream_id] = stream
            self.logger.info(f"Stream loopback ouvert: {device.name}")
            
            return stream
            
        except Exception as e:
            raise AudioStreamError(f"Erreur ouverture stream loopback: {e}")
    
    def close_stream(self, stream_id: str):
        """Ferme un stream spécifique"""
        if stream_id in self._streams:
            try:
                self._streams[stream_id].stop_stream()
                self._streams[stream_id].close()
                del self._streams[stream_id]
            except Exception as e:
                self.logger.warning(f"Erreur fermeture stream {stream_id}: {e}")
    
    def close_all(self):
        """Ferme tous les streams et libère PyAudio"""
        for stream_id in list(self._streams.keys()):
            self.close_stream(stream_id)
        
        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None
    
    def print_devices(self):
        """Affiche tous les périphériques disponibles"""
        print("\n" + "=" * 70)
        print("🎚️  PÉRIPHÉRIQUES AUDIO")
        print("=" * 70)
        
        for device in self.list_devices():
            device_type = []
            if device.is_input:
                device_type.append("IN")
            if device.is_output:
                device_type.append("OUT")
            if device.is_loopback:
                device_type.append("LOOP")
            
            type_str = "/".join(device_type)
            
            print(f"[{device.index:2d}] {device.name}")
            print(f"      Type: {type_str}, Rate: {int(device.default_sample_rate)}Hz")
        
        print("=" * 70)
```

Je continue avec les autres composants dans la partie 3...
### 7.2 Fichier: `src/vad.py`

```python
"""
Voice Activity Detection (VAD).
Détecte quand l'utilisateur parle pour éviter les traductions de silence.
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod

import numpy as np
import torch


class BaseVAD(ABC):
    """Interface de base pour les détecteurs d'activité vocale"""
    
    @abstractmethod
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Détecte si le chunk audio contient de la parole.
        
        Args:
            audio_chunk: Données audio brutes (int16)
            
        Returns:
            True si parole détectée
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Réinitialise l'état du VAD"""
        pass


class SileroVAD(BaseVAD):
    """
    VAD basé sur Silero (haute précision).
    Utilise un modèle neural pour détecter la parole.
    """
    
    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000,
                 min_silence_duration: float = 0.5):
        """
        Args:
            threshold: Seuil de probabilité (0-1) pour considérer comme parole
            sample_rate: Taux d'échantillonnage attendu
            min_silence_duration: Durée minimale de silence (en secondes)
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.min_silence_duration = min_silence_duration
        self.logger = logging.getLogger(__name__)
        
        # Compteur de silence
        self.silence_samples = 0
        self.max_silence_samples = int(min_silence_duration * sample_rate)
        
        # Chargement du modèle
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Silero VAD depuis torch.hub"""
        try:
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.model.eval()
            self.logger.info("✓ Silero VAD chargé")
            
        except Exception as e:
            self.logger.error(f"Erreur chargement Silero VAD: {e}")
            raise
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """Détecte la présence de parole dans le chunk audio"""
        try:
            # Conversion bytes -> numpy -> tensor
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float)
            
            # Inférence
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
            
            # Logique avec gestion du silence
            if speech_prob > self.threshold:
                self.silence_samples = 0
                return True
            else:
                self.silence_samples += len(audio_array)
                # Continue de retourner True pendant min_silence_duration
                return self.silence_samples < self.max_silence_samples
                
        except Exception as e:
            self.logger.warning(f"Erreur VAD: {e}")
            return True  # En cas d'erreur, on considère qu'il y a parole
    
    def reset(self):
        """Réinitialise le compteur de silence"""
        self.silence_samples = 0


class RMSVAD(BaseVAD):
    """
    VAD simple basé sur l'énergie RMS.
    Plus léger que Silero, adapté aux CPU faibles.
    """
    
    def __init__(self, threshold: float = 0.015, sample_rate: int = 16000,
                 min_silence_duration: float = 0.5):
        """
        Args:
            threshold: Seuil RMS normalisé (0-1)
            sample_rate: Taux d'échantillonnage
            min_silence_duration: Durée minimale de silence
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.min_silence_duration = min_silence_duration
        self.logger = logging.getLogger(__name__)
        
        self.silence_samples = 0
        self.max_silence_samples = int(min_silence_duration * sample_rate)
        
        self.logger.info(f"✓ RMS VAD initialisé (seuil: {threshold})")
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """Détecte la parole basé sur l'énergie RMS"""
        try:
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Calcul RMS normalisé
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)) / 32768.0
            
            if rms > self.threshold:
                self.silence_samples = 0
                return True
            else:
                self.silence_samples += len(audio_array)
                return self.silence_samples < self.max_silence_samples
                
        except Exception as e:
            self.logger.warning(f"Erreur RMS VAD: {e}")
            return True
    
    def reset(self):
        """Réinitialise le compteur de silence"""
        self.silence_samples = 0


class VADFactory:
    """Factory pour créer le bon type de VAD"""
    
    @staticmethod
    def create(backend: str = "silero", **kwargs) -> BaseVAD:
        """
        Crée une instance de VAD selon le backend demandé.
        
        Args:
            backend: "silero" ou "rms"
            **kwargs: Arguments passés au constructeur
            
        Returns:
            Instance de VAD
        """
        if backend == "silero":
            return SileroVAD(**kwargs)
        elif backend == "rms":
            return RMSVAD(**kwargs)
        else:
            raise ValueError(f"Backend VAD inconnu: {backend}")
```

### 7.3 Fichier: `src/stt.py`

```python
"""
Speech-to-Text avec Faster-Whisper.
Transcrit l'audio en texte avec haute précision.
"""

import logging
from typing import Optional, List, Tuple
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from .config import STTConfig


class STTProcessor:
    """
    Processeur Speech-to-Text basé sur Faster-Whisper.
    
    Usage:
        stt = STTProcessor(config)
        stt.add_audio(audio_chunk)
        text = stt.transcribe()
    """
    
    def __init__(self, config: STTConfig):
        """
        Args:
            config: Configuration STT
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Buffer audio
        self.audio_buffer: List[np.ndarray] = []
        self.buffer_duration: float = 0.0
        self.min_duration: float = 1.0  # Secondes minimum avant transcription
        
        # Modèle
        self.model: Optional[WhisperModel] = None
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Whisper"""
        self.logger.info(
            f"Chargement Whisper {self.config.model_size} "
            f"sur {self.config.device}..."
        )
        
        try:
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                download_root=self.config.download_root
            )
            
            self.logger.info(f"✓ Whisper {self.config.model_size} chargé")
            
        except Exception as e:
            self.logger.error(f"Erreur chargement Whisper: {e}")
            raise
    
    def add_audio(self, audio_chunk: bytes, sample_rate: int = 16000):
        """
        Ajoute un chunk audio au buffer.
        
        Args:
            audio_chunk: Données audio brutes (int16)
            sample_rate: Taux d'échantillonnage
        """
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        self.audio_buffer.append(audio_array)
        self.buffer_duration += len(audio_array) / sample_rate
    
    def transcribe(self, flush: bool = False) -> Optional[str]:
        """
        Transcrit le buffer audio si suffisamment de données.
        
        Args:
            flush: Force la transcription même avec peu de données
            
        Returns:
            Texte transcrit ou None si pas assez de données
        """
        if not self.audio_buffer:
            return None
        
        # Vérification durée minimale (sauf si flush)
        if not flush and self.buffer_duration < self.min_duration:
            return None
        
        try:
            # Concaténation et normalisation
            audio = np.concatenate(self.audio_buffer)
            audio_float = audio.astype(np.float32) / 32768.0
            
            # Transcription
            segments, info = self.model.transcribe(
                audio_float,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Extraction du texte
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)
            
            text = " ".join(text_parts).strip()
            
            # Reset du buffer
            self.clear_buffer()
            
            return text if text else None
            
        except Exception as e:
            self.logger.error(f"Erreur transcription: {e}")
            self.clear_buffer()
            return None
    
    def clear_buffer(self):
        """Vide le buffer audio"""
        self.audio_buffer = []
        self.buffer_duration = 0.0
    
    def set_language(self, language: str):
        """Change la langue de transcription"""
        self.config.language = language
```

### 7.4 Fichier: `src/translator.py`

```python
"""
Traduction avec NLLB-200 (Meta) ou Opus-MT.
Traduit le texte entre langues avec haute qualité.
"""

import logging
from typing import Optional, Dict

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from .config import TranslationConfig


class TranslatorProcessor:
    """
    Processeur de traduction basé sur NLLB-200 ou Opus-MT.
    
    Usage:
        translator = TranslatorProcessor(config)
        text_en = translator.translate("Bonjour", "fr", "en")
    """
    
    # Codes de langue NLLB
    NLLB_LANG_CODES = {
        "fr": "fra_Latn",
        "en": "eng_Latn",
        "es": "spa_Latn",
        "de": "deu_Latn",
        "it": "ita_Latn",
        "pt": "por_Latn",
        "nl": "nld_Latn",
        "pl": "pol_Latn",
        "ru": "rus_Cyrl",
        "zh": "zho_Hans",
        "ja": "jpn_Jpan",
        "ko": "kor_Hang",
        "ar": "arb_Arab"
    }
    
    def __init__(self, config: TranslationConfig):
        """
        Args:
            config: Configuration de traduction
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.tokenizer = None
        self.model = None
        self.is_nllb = "nllb" in config.model_name.lower()
        
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle de traduction"""
        self.logger.info(f"Chargement modèle: {self.config.model_name}...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
            
            # Déplacement sur GPU si disponible
            if self.config.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to("cuda")
            
            self.model.eval()
            
            self.logger.info(f"✓ Modèle de traduction chargé sur {self.config.device}")
            
        except Exception as e:
            self.logger.error(f"Erreur chargement traduction: {e}")
            raise
    
    def translate(self, text: str, source_lang: str = "fr", 
                  target_lang: str = "en") -> str:
        """
        Traduit un texte d'une langue à une autre.
        
        Args:
            text: Texte à traduire
            source_lang: Code langue source (ex: "fr")
            target_lang: Code langue cible (ex: "en")
            
        Returns:
            Texte traduit
        """
        if not text or not text.strip():
            return ""
        
        try:
            if self.is_nllb:
                return self._translate_nllb(text, source_lang, target_lang)
            else:
                return self._translate_opus(text)
                
        except Exception as e:
            self.logger.error(f"Erreur traduction: {e}")
            return text  # Retourne le texte original en cas d'erreur
    
    def _translate_nllb(self, text: str, source_lang: str, 
                        target_lang: str) -> str:
        """Traduction avec NLLB"""
        # Conversion des codes de langue
        src_code = self.NLLB_LANG_CODES.get(source_lang, "fra_Latn")
        tgt_code = self.NLLB_LANG_CODES.get(target_lang, "eng_Latn")
        
        # Tokenization
        self.tokenizer.src_lang = src_code
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_length
        )
        
        # Déplacement sur GPU si nécessaire
        if self.config.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # ID du token de langue cible
        forced_bos_token_id = self.tokenizer.lang_code_to_id[tgt_code]
        
        # Génération
        with torch.no_grad():
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=self.config.max_length,
                num_beams=self.config.num_beams,
                early_stopping=True
            )
        
        # Décodage
        translation = self.tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True
        )[0]
        
        return translation.strip()
    
    def _translate_opus(self, text: str) -> str:
        """Traduction avec Opus-MT (plus simple)"""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_length
        )
        
        if self.config.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            generated_tokens = self.model.generate(
                **inputs,
                max_length=self.config.max_length,
                num_beams=self.config.num_beams,
                early_stopping=True
            )
        
        translation = self.tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True
        )[0]
        
        return translation.strip()
    
    def set_languages(self, source_lang: str, target_lang: str):
        """Configure les langues source et cible"""
        self.config.source_lang = self.NLLB_LANG_CODES.get(source_lang, source_lang)
        self.config.target_lang = self.NLLB_LANG_CODES.get(target_lang, target_lang)
```

### 7.5 Fichier: `src/tts.py`

```python
"""
Text-to-Speech avec Piper.
Synthétise la parole à partir du texte traduit.
"""

import logging
from typing import Optional, Generator
from pathlib import Path
import io
import wave

import numpy as np

from .config import TTSConfig


class TTSProcessor:
    """
    Processeur Text-to-Speech basé sur Piper.
    
    Usage:
        tts = TTSProcessor(config)
        audio_data = tts.synthesize("Hello world")
    """
    
    def __init__(self, config: TTSConfig, language: str = "fr"):
        """
        Args:
            config: Configuration TTS
            language: Langue de sortie ("fr" ou "en")
        """
        self.config = config
        self.language = language
        self.logger = logging.getLogger(__name__)
        
        self.voice = None
        self._load_voice()
    
    def _load_voice(self):
        """Charge la voix Piper pour la langue configurée"""
        try:
            from piper import PiperVoice
            
            # Sélection de la voix selon la langue
            if self.language == "fr":
                voice_name = self.config.voice_fr
            else:
                voice_name = self.config.voice_en
            
            # Chemin du modèle
            model_path = Path(self.config.model_path) / voice_name
            onnx_file = model_path / f"{voice_name}.onnx"
            
            if not onnx_file.exists():
                self.logger.warning(f"Voix Piper non trouvée: {onnx_file}")
                self.logger.warning("Le TTS sera désactivé")
                return
            
            self.voice = PiperVoice.load(str(onnx_file))
            self.logger.info(f"✓ Piper TTS chargé ({self.language})")
            
        except ImportError:
            self.logger.warning("Piper TTS non installé")
        except Exception as e:
            self.logger.warning(f"Erreur chargement Piper: {e}")
    
    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthétise du texte en audio.
        
        Args:
            text: Texte à synthétiser
            
        Returns:
            Données audio brutes (int16) ou None si erreur
        """
        if not text or not text.strip():
            return None
        
        if not self.voice:
            self.logger.warning("TTS non disponible")
            return None
        
        try:
            # Synthèse
            audio_stream = self.voice.synthesize_stream_raw(text)
            
            # Collecte des chunks
            audio_chunks = []
            for chunk in audio_stream:
                audio_chunks.append(chunk)
            
            if not audio_chunks:
                return None
            
            audio_data = b''.join(audio_chunks)
            
            # Rééchantillonnage si nécessaire (Piper sort en 22050Hz)
            # Note: On peut gérer cela côté output stream
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Erreur synthèse TTS: {e}")
            return None
    
    def synthesize_stream(self, text: str) -> Generator[bytes, None, None]:
        """
        Synthétise du texte en streaming.
        
        Args:
            text: Texte à synthétiser
            
        Yields:
            Chunks audio
        """
        if not text or not self.voice:
            return
        
        try:
            for chunk in self.voice.synthesize_stream_raw(text):
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Erreur streaming TTS: {e}")
    
    def set_language(self, language: str):
        """Change la langue de synthèse"""
        if language != self.language:
            self.language = language
            self._load_voice()
```

---

## 8. DÉVELOPPEMENT - PHASE 4: INTÉGRATION COMPLÈTE

### 8.1 Fichier: `src/pipeline.py`

```python
"""
Pipeline de traduction complet.
Orchestre VAD, STT, Translation, TTS pour un flux audio.
"""

import asyncio
import logging
import time
from typing import Optional, Callable
from dataclasses import dataclass, field

import pyaudiowpatch as pyaudio

from .config import AppConfig, AudioConfig, FlowDirection
from .audio_manager import AudioManager, DeviceInfo
from .vad import VADFactory, BaseVAD
from .stt import STTProcessor
from .translator import TranslatorProcessor
from .tts import TTSProcessor


@dataclass
class PipelineStats:
    """Statistiques du pipeline"""
    total_translations: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    
    def update(self, latency_ms: float):
        """Met à jour les statistiques"""
        self.total_translations += 1
        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / self.total_translations
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)


class TranslationPipeline:
    """
    Pipeline de traduction bidirectionnel pour un flux.
    
    Usage:
        pipeline = TranslationPipeline(
            direction=FlowDirection.OUTGOING,
            config=app_config
        )
        await pipeline.initialize()
        await pipeline.run()
    """
    
    def __init__(self, direction: FlowDirection, config: AppConfig):
        """
        Args:
            direction: OUTGOING (FR→EN) ou INCOMING (EN→FR)
            config: Configuration de l'application
        """
        self.direction = direction
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{direction.value}")
        
        # Configuration des langues selon la direction
        if direction == FlowDirection.OUTGOING:
            self.source_lang = "fr"
            self.target_lang = "en"
            self.tts_lang = "en"
        else:
            self.source_lang = "en"
            self.target_lang = "fr"
            self.tts_lang = "fr"
        
        # Composants (initialisés dans initialize())
        self.audio_manager: Optional[AudioManager] = None
        self.vad: Optional[BaseVAD] = None
        self.stt: Optional[STTProcessor] = None
        self.translator: Optional[TranslatorProcessor] = None
        self.tts: Optional[TTSProcessor] = None
        
        # Streams
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        
        # État
        self.is_running = False
        self.stats = PipelineStats()
        
        # Callback optionnel pour les transcriptions
        self.on_transcript: Optional[Callable[[str, str, float], None]] = None
    
    async def initialize(self):
        """Initialise tous les composants du pipeline"""
        self.logger.info(f"Initialisation pipeline {self.direction.value}...")
        
        # Audio Manager
        self.audio_manager = AudioManager()
        
        # VAD
        self.vad = VADFactory.create(
            backend=self.config.vad.backend,
            threshold=self.config.vad.threshold,
            sample_rate=self.config.audio.sample_rate,
            min_silence_duration=self.config.vad.min_silence_duration
        )
        
        # STT
        stt_config = self.config.stt
        stt_config.language = self.source_lang
        self.stt = STTProcessor(stt_config)
        
        # Translator
        self.translator = TranslatorProcessor(self.config.translation)
        
        # TTS
        self.tts = TTSProcessor(self.config.tts, language=self.tts_lang)
        
        # Configuration des streams audio
        await self._setup_audio_streams()
        
        self.logger.info(f"✓ Pipeline {self.direction.value} initialisé")
    
    async def _setup_audio_streams(self):
        """Configure les streams d'entrée et de sortie"""
        audio_config = self.config.audio
        
        if self.direction == FlowDirection.OUTGOING:
            # Input: Microphone physique (défaut)
            self.input_stream = self.audio_manager.open_input_stream(
                config=audio_config,
                device_pattern=audio_config.input_device_pattern or None,
                stream_id=f"{self.direction.value}_in"
            )
            
            # Output: VB-Cable Input 1
            self.output_stream = self.audio_manager.open_output_stream(
                config=audio_config,
                device_pattern=audio_config.vbcable_input_pattern,
                stream_id=f"{self.direction.value}_out"
            )
            
        else:  # INCOMING
            # Input: VB-Cable B (Loopback)
            self.input_stream = self.audio_manager.open_loopback_stream(
                config=audio_config,
                device_pattern=audio_config.vbcable_output_pattern,
                stream_id=f"{self.direction.value}_in"
            )
            
            # Output: Haut-parleurs (défaut)
            self.output_stream = self.audio_manager.open_output_stream(
                config=audio_config,
                device_pattern=audio_config.output_device_pattern or None,
                stream_id=f"{self.direction.value}_out"
            )
    
    async def run(self):
        """Boucle principale du pipeline"""
        self.is_running = True
        self.logger.info(f"▶ Démarrage pipeline {self.direction.value}")
        
        try:
            while self.is_running:
                try:
                    # Lecture audio
                    audio_chunk = self.input_stream.read(
                        self.config.audio.chunk_size,
                        exception_on_overflow=False
                    )
                    
                    # VAD: vérification parole
                    if self.vad.is_speech(audio_chunk):
                        # Ajout au buffer STT
                        self.stt.add_audio(
                            audio_chunk,
                            self.config.audio.sample_rate
                        )
                        
                        # Tentative de transcription
                        transcript = self.stt.transcribe(flush=False)
                        
                        if transcript:
                            await self._process_transcript(transcript)
                    
                    # Yield pour permettre à d'autres tâches de s'exécuter
                    await asyncio.sleep(0.001)
                    
                except Exception as e:
                    self.logger.error(f"Erreur dans la boucle: {e}")
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            self.logger.info(f"⏸ Pipeline {self.direction.value} annulé")
        finally:
            await self.cleanup()
    
    async def _process_transcript(self, text: str):
        """Traite une transcription complète"""
        start_time = time.time()
        
        self.logger.info(
            f"[{self.direction.value}] 📝 {self.source_lang.upper()}: {text}"
        )
        
        # Traduction
        translation = self.translator.translate(
            text,
            self.source_lang,
            self.target_lang
        )
        
        self.logger.info(
            f"[{self.direction.value}] 🔄 {self.target_lang.upper()}: {translation}"
        )
        
        # Synthèse TTS
        if self.tts:
            audio_data = self.tts.synthesize(translation)
            
            if audio_data and self.output_stream:
                try:
                    self.output_stream.write(audio_data)
                except Exception as e:
                    self.logger.warning(f"Erreur écriture audio: {e}")
        
        # Statistiques
        latency_ms = (time.time() - start_time) * 1000
        self.stats.update(latency_ms)
        
        self.logger.info(
            f"[{self.direction.value}] ⏱ Latence: {latency_ms:.0f}ms"
        )
        
        # Callback
        if self.on_transcript:
            self.on_transcript(text, translation, latency_ms)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        self.is_running = False
        
        if self.audio_manager:
            self.audio_manager.close_all()
        
        self.logger.info(
            f"✓ Pipeline {self.direction.value} arrêté "
            f"({self.stats.total_translations} traductions)"
        )
    
    def get_stats(self) -> dict:
        """Retourne les statistiques du pipeline"""
        return {
            "direction": self.direction.value,
            "total_translations": self.stats.total_translations,
            "avg_latency_ms": round(self.stats.avg_latency_ms, 1),
            "min_latency_ms": round(self.stats.min_latency_ms, 1),
            "max_latency_ms": round(self.stats.max_latency_ms, 1)
        }


class BilingualTranslator:
    """
    Orchestrateur principal gérant les deux pipelines.
    
    Usage:
        translator = BilingualTranslator(config)
        await translator.start()
        # ...
        await translator.stop()
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Pipelines
        self.outgoing = TranslationPipeline(FlowDirection.OUTGOING, config)
        self.incoming = TranslationPipeline(FlowDirection.INCOMING, config)
        
        # Tâches async
        self.tasks = []
    
    async def start(self):
        """Démarre les deux pipelines"""
        self.logger.info("=" * 70)
        self.logger.info("🚀 TRADUCTEUR LOCAL BIDIRECTIONNEL - DÉMARRAGE")
        self.logger.info("=" * 70)
        
        # Initialisation
        await self.outgoing.initialize()
        await self.incoming.initialize()
        
        self.logger.info("")
        self.logger.info("✓ Tous les flux sont opérationnels (100% LOCAL)")
        self.logger.info("")
        self.logger.info("📞 OUTGOING: Micro → FR→EN → VB-Cable Input 1 → Teams")
        self.logger.info("📞 INCOMING: Teams → VB-Cable B → EN→FR → Haut-parleurs")
        self.logger.info("")
        self.logger.info("💰 Coût: $0.00 | 🔒 Données: 100% privées")
        self.logger.info("")
        self.logger.info("Appuyez sur Ctrl+C pour arrêter")
        self.logger.info("=" * 70)
        
        # Lancement parallèle
        self.tasks = [
            asyncio.create_task(self.outgoing.run()),
            asyncio.create_task(self.incoming.run())
        ]
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop(self):
        """Arrête proprement les pipelines"""
        self.logger.info("\n🛑 Arrêt en cours...")
        
        for task in self.tasks:
            task.cancel()
        
        await self.outgoing.cleanup()
        await self.incoming.cleanup()
        
        self.logger.info("✓ Arrêt complet")
    
    def get_stats(self) -> dict:
        """Retourne les statistiques combinées"""
        return {
            "outgoing": self.outgoing.get_stats(),
            "incoming": self.incoming.get_stats()
        }
```

### 8.2 Fichier: `src/main.py`

```python
"""
Point d'entrée principal de l'application.
"""

import asyncio
import logging
import signal
import sys
import argparse
from pathlib import Path

from .config import AppConfig
from .model_manager import ModelManager
from .pipeline import BilingualTranslator


def setup_logging(level: str = "INFO", log_file: str = None):
    """Configure le système de logging"""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        handlers=handlers
    )


def parse_args():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Traducteur Bidirectionnel Temps Réel"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Fichier de configuration YAML"
    )
    
    parser.add_argument(
        "--profile", "-p",
        type=str,
        choices=["high_performance", "balanced", "low_resource", "cpu_only"],
        default=None,
        help="Profil de performance (surcharge la détection auto)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Fichier de log"
    )
    
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Liste les périphériques audio et quitte"
    )
    
    return parser.parse_args()


async def main():
    """Fonction principale async"""
    args = parse_args()
    
    # Configuration du logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level, log_file=args.log_file)
    
    logger = logging.getLogger(__name__)
    
    # Mode liste des périphériques
    if args.list_devices:
        from .audio_manager import AudioManager
        manager = AudioManager()
        manager.print_devices()
        return
    
    # Chargement de la configuration
    if args.config and Path(args.config).exists():
        config = AppConfig.from_yaml(args.config)
    else:
        config = AppConfig()
    
    # Détection matérielle et configuration des modèles
    try:
        model_manager = ModelManager(config, auto_detect=True)
        model_manager.initialize(verbose=True)
        
        # Surcharge du profil si spécifié
        if args.profile:
            config.apply_profile(args.profile)
            
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        sys.exit(1)
    
    # Création du traducteur
    translator = BilingualTranslator(config)
    
    # Gestion du signal d'arrêt
    def signal_handler(sig, frame):
        logger.info("\n⚠️ Signal d'interruption reçu")
        asyncio.create_task(translator.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrage
    try:
        await translator.start()
    except KeyboardInterrupt:
        await translator.stop()
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        await translator.stop()
        sys.exit(1)


def run():
    """Point d'entrée pour le script"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
```

Je continue avec la partie 4 contenant les outils, tests et documentation...
## 9. DÉVELOPPEMENT - PHASE 5: OUTILS ET UTILITAIRES

### 9.1 Fichier: `tools/setup_check.py`

```python
#!/usr/bin/env python
"""
Vérification complète de l'installation.
À exécuter après l'installation pour valider que tout fonctionne.
"""

import sys
import platform
from pathlib import Path


def check_python_version():
    """Vérifie la version Python"""
    print("\n📍 Vérification Python...")
    version = sys.version_info
    
    if version.major == 3 and version.minor >= 10:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ✗ Python {version.major}.{version.minor} (requis: 3.10+)")
        return False


def check_dependencies():
    """Vérifie les dépendances Python"""
    print("\n📦 Vérification des dépendances...")
    
    dependencies = {
        "torch": "PyTorch",
        "faster_whisper": "Faster-Whisper (STT)",
        "transformers": "Transformers (Traduction)",
        "pyaudiowpatch": "PyAudioWPatch (Audio)",
        "numpy": "NumPy",
        "piper": "Piper TTS (optionnel)"
    }
    
    all_ok = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"   ✓ {description}")
        except ImportError:
            if "optionnel" in description.lower():
                print(f"   ⚠ {description} - non installé")
            else:
                print(f"   ✗ {description} - MANQUANT")
                all_ok = False
    
    return all_ok


def check_cuda():
    """Vérifie le support CUDA"""
    print("\n🖥️  Vérification GPU...")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory // (1024**3)
            print(f"   ✓ CUDA disponible: {gpu_name} ({vram}GB)")
            return True
        else:
            print("   ⚠ CUDA non disponible (mode CPU)")
            return True  # Pas bloquant
            
    except ImportError:
        print("   ⚠ PyTorch non installé")
        return False


def check_vbcable():
    """Vérifie l'installation de VB-Cable"""
    print("\n🎚️  Vérification VB-Cable...")
    
    try:
        import pyaudiowpatch as pyaudio
        
        p = pyaudio.PyAudio()
        vb_cable_found = False
        vb_cable_b_found = False
        
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            name_lower = info['name'].lower()
            
            if 'cable input' in name_lower and 'vb-audio' in name_lower:
                vb_cable_found = True
            if 'cable-b' in name_lower:
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


def check_models():
    """Vérifie la présence des modèles"""
    print("\n🤖 Vérification des modèles...")
    
    models_dir = Path("./models")
    
    whisper_ok = (models_dir / "whisper").exists()
    nllb_ok = (models_dir / "nllb").exists()
    piper_ok = (models_dir / "piper").exists()
    
    if whisper_ok:
        print("   ✓ Dossier Whisper présent")
    else:
        print("   ⚠ Whisper: sera téléchargé au premier lancement")
    
    if nllb_ok:
        print("   ✓ Dossier NLLB présent")
    else:
        print("   ⚠ NLLB: sera téléchargé au premier lancement")
    
    if piper_ok:
        print("   ✓ Dossier Piper présent")
    else:
        print("   ⚠ Piper: sera téléchargé au premier lancement")
    
    return True  # Les modèles se téléchargent automatiquement


def print_summary(results):
    """Affiche le résumé"""
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
        print("   ./scripts/run.bat  (Windows)")
    else:
        print("\n⚠️  INSTALLATION INCOMPLÈTE")
        print("\nCorrigez les erreurs ci-dessus puis relancez ce script.")
    
    print()


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🔍 VÉRIFICATION DE L'INSTALLATION")
    print("=" * 70)
    
    results = {
        "Python 3.10+": check_python_version(),
        "Dépendances": check_dependencies(),
        "GPU (CUDA)": check_cuda(),
        "VB-Cable": check_vbcable(),
        "Modèles": check_models()
    }
    
    print_summary(results)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 9.2 Fichier: `tools/audio_diagnostic.py`

```python
#!/usr/bin/env python
"""
Diagnostic complet des périphériques audio.
Liste et teste les périphériques disponibles.
"""

import sys
sys.path.insert(0, '.')

from src.audio_manager import AudioManager


def main():
    """Diagnostic audio"""
    print("\n" + "=" * 70)
    print("🎚️  DIAGNOSTIC AUDIO")
    print("=" * 70)
    
    manager = AudioManager()
    manager.print_devices()
    
    # Recherche des périphériques clés
    print("\n📍 RECHERCHE DES PÉRIPHÉRIQUES REQUIS:")
    print("-" * 70)
    
    # Microphone par défaut
    try:
        mic = manager.get_default_input_device()
        print(f"✓ Microphone par défaut: {mic.name}")
    except Exception as e:
        print(f"✗ Microphone par défaut: {e}")
    
    # Haut-parleurs par défaut
    try:
        speakers = manager.get_default_output_device()
        print(f"✓ Haut-parleurs par défaut: {speakers.name}")
    except Exception as e:
        print(f"✗ Haut-parleurs par défaut: {e}")
    
    # VB-Cable Input
    try:
        vbcable = manager.find_device("CABLE Input", output_only=True)
        print(f"✓ VB-Cable Input: {vbcable.name}")
    except Exception as e:
        print(f"✗ VB-Cable Input: {e}")
    
    # VB-Cable B (Loopback)
    try:
        vbcable_b = manager.find_loopback_device("CABLE-B")
        print(f"✓ VB-Cable B Loopback: {vbcable_b.name}")
    except Exception as e:
        print(f"⚠ VB-Cable B Loopback: {e}")
    
    print("-" * 70)
    
    manager.close_all()


if __name__ == "__main__":
    main()
```

### 9.3 Fichier: `tools/benchmark.py`

```python
#!/usr/bin/env python
"""
Benchmark de performance du système.
Mesure la latence de chaque composant.
"""

import sys
import time
import numpy as np
import torch

sys.path.insert(0, '.')

from src.config import AppConfig
from src.model_manager import ModelManager


def benchmark_stt(config):
    """Benchmark du STT"""
    print("\n🎤 Benchmark STT (Faster-Whisper)...")
    
    from src.stt import STTProcessor
    
    stt = STTProcessor(config.stt)
    
    # Génération d'audio de test (3 secondes de bruit)
    duration = 3.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    audio = np.random.randint(-1000, 1000, samples, dtype=np.int16)
    audio_bytes = audio.tobytes()
    
    # Benchmark
    stt.add_audio(audio_bytes, sample_rate)
    
    start = time.time()
    result = stt.transcribe(flush=True)
    elapsed = (time.time() - start) * 1000
    
    print(f"   Durée audio: {duration}s")
    print(f"   Temps traitement: {elapsed:.0f}ms")
    print(f"   Ratio: {elapsed/(duration*1000):.2f}x temps réel")
    
    return elapsed


def benchmark_translation(config):
    """Benchmark de la traduction"""
    print("\n🔄 Benchmark Traduction (NLLB)...")
    
    from src.translator import TranslatorProcessor
    
    translator = TranslatorProcessor(config.translation)
    
    test_texts = [
        "Bonjour, comment allez-vous?",
        "Je voudrais commander cinq cents unités du produit référence XYZ.",
        "Le délai de livraison est de trois semaines après confirmation."
    ]
    
    total_time = 0
    for text in test_texts:
        start = time.time()
        result = translator.translate(text, "fr", "en")
        elapsed = (time.time() - start) * 1000
        total_time += elapsed
        
        print(f"   '{text[:40]}...'")
        print(f"   → {elapsed:.0f}ms")
    
    avg_time = total_time / len(test_texts)
    print(f"\n   Temps moyen: {avg_time:.0f}ms")
    
    return avg_time


def benchmark_tts(config):
    """Benchmark du TTS"""
    print("\n🔊 Benchmark TTS (Piper)...")
    
    try:
        from src.tts import TTSProcessor
        
        tts = TTSProcessor(config.tts, language="en")
        
        if not tts.voice:
            print("   ⚠ Piper non disponible")
            return 0
        
        test_text = "Hello, this is a test of the text to speech system."
        
        start = time.time()
        audio = tts.synthesize(test_text)
        elapsed = (time.time() - start) * 1000
        
        if audio:
            audio_duration = len(audio) / (22050 * 2) * 1000  # 22050Hz, 16-bit
            print(f"   Texte: {len(test_text)} caractères")
            print(f"   Audio généré: {audio_duration:.0f}ms")
            print(f"   Temps traitement: {elapsed:.0f}ms")
        
        return elapsed
        
    except ImportError:
        print("   ⚠ Piper non installé")
        return 0


def main():
    """Exécute tous les benchmarks"""
    print("=" * 70)
    print("⏱️  BENCHMARK DE PERFORMANCE")
    print("=" * 70)
    
    # Configuration
    config = AppConfig()
    manager = ModelManager(config, auto_detect=True)
    manager.initialize(verbose=True)
    
    # Benchmarks
    stt_time = benchmark_stt(config)
    translation_time = benchmark_translation(config)
    tts_time = benchmark_tts(config)
    
    # Résumé
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
```

### 9.4 Fichier: `tools/test_translation.py`

```python
#!/usr/bin/env python
"""
Test rapide de la traduction FR↔EN.
Permet de vérifier que les modèles fonctionnent.
"""

import sys
sys.path.insert(0, '.')

from src.config import AppConfig
from src.model_manager import ModelManager
from src.translator import TranslatorProcessor


def main():
    """Test interactif de traduction"""
    print("=" * 70)
    print("🔄 TEST DE TRADUCTION FR ↔ EN")
    print("=" * 70)
    
    # Configuration
    config = AppConfig()
    manager = ModelManager(config, auto_detect=True)
    manager.initialize(verbose=False)
    
    # Chargement du traducteur
    print("\nChargement du modèle...")
    translator = TranslatorProcessor(config.translation)
    
    print("\n✓ Prêt!")
    print("Entrez du texte en français pour le traduire en anglais.")
    print("Préfixez par 'en:' pour traduire de l'anglais vers le français.")
    print("Tapez 'quit' pour quitter.\n")
    
    while True:
        try:
            text = input("→ ").strip()
            
            if text.lower() == 'quit':
                break
            
            if text.startswith("en:"):
                # Anglais → Français
                text = text[3:].strip()
                result = translator.translate(text, "en", "fr")
                print(f"← {result}\n")
            else:
                # Français → Anglais
                result = translator.translate(text, "fr", "en")
                print(f"← {result}\n")
                
        except KeyboardInterrupt:
            break
    
    print("\nAu revoir!")


if __name__ == "__main__":
    main()
```

---

## 10. TESTS ET VALIDATION

### 10.1 Fichier: `tests/conftest.py`

```python
"""
Configuration et fixtures pour pytest.
"""

import pytest
import numpy as np

from src.config import AppConfig, AudioConfig, STTConfig


@pytest.fixture
def app_config():
    """Configuration de test"""
    config = AppConfig()
    config.stt.model_size = "tiny"  # Modèle léger pour les tests
    config.stt.device = "cpu"
    config.translation.model_name = "Helsinki-NLP/opus-mt-fr-en"
    config.translation.device = "cpu"
    return config


@pytest.fixture
def audio_config():
    """Configuration audio de test"""
    return AudioConfig(
        sample_rate=16000,
        channels=1,
        chunk_size=1024
    )


@pytest.fixture
def sample_audio():
    """Génère un échantillon audio de test"""
    duration = 1.0  # 1 seconde
    sample_rate = 16000
    samples = int(duration * sample_rate)
    audio = np.random.randint(-1000, 1000, samples, dtype=np.int16)
    return audio.tobytes()
```

### 10.2 Fichier: `tests/test_hardware.py`

```python
"""
Tests pour la détection matérielle.
"""

import pytest
from src.hardware_detector import HardwareDetector, HardwareInfo
from src.config import HardwareLevel


def test_hardware_detection():
    """Test de la détection matérielle"""
    detector = HardwareDetector()
    info = detector.detect()
    
    assert isinstance(info, HardwareInfo)
    assert info.cpu_cores > 0
    assert info.ram_gb > 0
    assert info.level in HardwareLevel


def test_hardware_level_assignment():
    """Test de l'assignation du niveau"""
    detector = HardwareDetector()
    info = detector.detect()
    
    # Le niveau doit être cohérent avec les capacités
    if info.has_cuda and info.vram_mb >= 12000:
        assert info.level == HardwareLevel.HIGH
    elif not info.has_cuda and not info.has_directml:
        assert info.level == HardwareLevel.CPU_ONLY
```

### 10.3 Fichier: `tests/test_vad.py`

```python
"""
Tests pour le VAD.
"""

import pytest
import numpy as np

from src.vad import RMSVAD, VADFactory


def test_rms_vad_silence():
    """Test VAD avec silence"""
    vad = RMSVAD(threshold=0.1)
    
    # Audio silencieux
    silence = np.zeros(1600, dtype=np.int16).tobytes()
    
    # Premier appel: devrait retourner False après accumulation
    for _ in range(10):
        result = vad.is_speech(silence)
    
    assert result == False


def test_rms_vad_speech():
    """Test VAD avec signal fort"""
    vad = RMSVAD(threshold=0.01)
    
    # Audio avec signal fort
    signal = np.random.randint(-10000, 10000, 1600, dtype=np.int16)
    audio = signal.tobytes()
    
    assert vad.is_speech(audio) == True


def test_vad_factory():
    """Test de la factory VAD"""
    rms_vad = VADFactory.create("rms", threshold=0.02)
    assert isinstance(rms_vad, RMSVAD)
```

### 10.4 Fichier: `tests/test_translator.py`

```python
"""
Tests pour le traducteur.
"""

import pytest
from src.config import TranslationConfig
from src.translator import TranslatorProcessor


@pytest.fixture
def translator():
    """Crée un traducteur de test (léger)"""
    config = TranslationConfig()
    config.model_name = "Helsinki-NLP/opus-mt-fr-en"
    config.device = "cpu"
    return TranslatorProcessor(config)


def test_translation_fr_to_en(translator):
    """Test traduction FR→EN"""
    result = translator.translate("Bonjour", "fr", "en")
    assert result.lower() in ["hello", "good morning", "hi"]


def test_translation_empty_string(translator):
    """Test avec chaîne vide"""
    result = translator.translate("", "fr", "en")
    assert result == ""


def test_translation_whitespace(translator):
    """Test avec espaces"""
    result = translator.translate("   ", "fr", "en")
    assert result == ""
```

---

## 11. DOCUMENTATION

### 11.1 Fichier: `docs/INSTALLATION.md`

Crée un guide d'installation complet avec:
- Prérequis système (Windows, Python, GPU)
- Installation de VB-Cable
- Installation des dépendances Python
- Configuration des clés API (si version cloud)
- Premier lancement
- Vérification de l'installation

### 11.2 Fichier: `docs/USAGE.md`

Crée un guide d'utilisation avec:
- Démarrage de l'application
- Configuration de Teams/Zoom
- Utilisation pendant un appel
- Commandes disponibles
- Arrêt propre

### 11.3 Fichier: `docs/TROUBLESHOOTING.md`

Crée un guide de dépannage avec:
- Erreurs courantes et solutions
- Problèmes audio
- Problèmes de latence
- Problèmes de modèles
- FAQ

### 11.4 Fichier: `docs/CONFIGURATION.md`

Crée un guide de configuration avec:
- Fichiers de configuration YAML
- Options disponibles
- Profils de performance
- Personnalisation avancée

---

## 12. LIVRAISON FINALE

### 12.1 Scripts d'Installation

#### `scripts/install_windows.bat`

```batch
@echo off
echo ================================================================
echo   INSTALLATION - Traducteur Bidirectionnel
echo ================================================================
echo.

REM Vérification Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trouvé. Installez Python 3.10+ depuis python.org
    pause
    exit /b 1
)

REM Création environnement virtuel
echo 📦 Création de l'environnement virtuel...
python -m venv venv
call venv\Scripts\activate

REM Installation PyTorch
echo 📦 Installation de PyTorch...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

REM Installation dépendances
echo 📦 Installation des dépendances...
pip install -r requirements.txt

REM Vérification
echo.
echo 🔍 Vérification de l'installation...
python tools/setup_check.py

echo.
echo ================================================================
echo   INSTALLATION TERMINÉE
echo ================================================================
echo.
echo Pour démarrer: scripts\run.bat
pause
```

#### `scripts/run.bat`

```batch
@echo off
call venv\Scripts\activate
python -m src.main %*
```

### 12.2 Fichier: `requirements.txt`

```
# Core
numpy>=1.24.0,<2.0.0
pyyaml>=6.0
tqdm>=4.65.0

# Audio
pyaudiowpatch>=0.2.12.9
soundfile>=0.12.0

# Deep Learning
torch>=2.0.0
transformers>=4.35.0
accelerate>=0.25.0
sentencepiece>=0.1.99

# STT
faster-whisper>=1.0.0
ctranslate2>=3.24.0

# TTS
piper-tts>=1.2.0
onnxruntime>=1.16.0

# Monitoring
psutil>=5.9.0
colorlog>=6.8.0
```

### 12.3 Fichier: `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "izvox"
version = "2.0.0"
description = "Traducteur bidirectionnel temps réel pour visioconférences"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "Expert Python AI"}
]
keywords = ["translation", "real-time", "speech-to-text", "tts", "teams", "zoom"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Multimedia :: Sound/Audio :: Speech"
]

[project.scripts]
izvox = "src.main:run"

[project.urls]
Homepage = "https://github.com/user/izvox"
Documentation = "https://github.com/user/izvox/docs"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

### 12.4 Fichier: `README.md`

```markdown
# 🚀 Traducteur Bidirectionnel Temps Réel

Traduction instantanée FR↔EN pour vos visioconférences Teams, Zoom, Meet.

## ✨ Caractéristiques

- ⚡ **Latence ultra-basse** : < 600ms
- 💰 **100% gratuit** : Fonctionne entièrement en local
- 🔒 **Privé** : Aucune donnée envoyée sur Internet
- 🎯 **Adaptatif** : S'ajuste automatiquement à votre matériel

## 🚀 Installation Rapide

```bash
# 1. Cloner le projet
git clone https://github.com/user/izvox.git
cd izvox

# 2. Installer (Windows)
scripts\install_windows.bat

# 3. Lancer
scripts\run.bat
```

## 📖 Documentation

- [Installation détaillée](docs/INSTALLATION.md)
- [Guide d'utilisation](docs/USAGE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Dépannage](docs/TROUBLESHOOTING.md)

## 📋 Prérequis

- Windows 10/11
- Python 3.10+
- GPU NVIDIA (recommandé) ou CPU
- VB-Audio Virtual Cable

## 📄 Licence

MIT License
```

---

## CHECKLIST FINALE

Avant de livrer, vérifie que:

### Code
- [ ] Tous les fichiers `src/*.py` sont créés et fonctionnels
- [ ] Tous les fichiers `tests/*.py` sont créés
- [ ] Tous les fichiers `tools/*.py` sont créés
- [ ] Les scripts `scripts/*.bat` sont créés

### Configuration
- [ ] `requirements.txt` est complet
- [ ] `pyproject.toml` est valide
- [ ] Fichiers YAML dans `config/` sont créés
- [ ] `.gitignore` est présent

### Documentation
- [ ] `README.md` est clair et complet
- [ ] `docs/INSTALLATION.md` couvre tous les cas
- [ ] `docs/USAGE.md` est pratique
- [ ] `docs/TROUBLESHOOTING.md` couvre les erreurs courantes

### Tests
- [ ] `python tools/setup_check.py` passe
- [ ] `pytest tests/` passe (tests unitaires)
- [ ] Test manuel de bout en bout avec Teams/Zoom

### Qualité
- [ ] Code formaté avec Black
- [ ] Types hints présents
- [ ] Docstrings complètes
- [ ] Logging cohérent
- [ ] Gestion d'erreurs robuste

---

## COMMANDES DE DÉVELOPPEMENT

```bash
# Installation en mode développement
pip install -e .

# Formatage du code
pip install black
black src/ tests/ tools/

# Vérification des types
pip install mypy
mypy src/

# Lancer les tests
pip install pytest pytest-asyncio
pytest tests/ -v

# Benchmark
python tools/benchmark.py

# Diagnostic audio
python tools/audio_diagnostic.py

# Test de traduction interactif
python tools/test_translation.py

# Lancement de l'application
python -m src.main
python -m src.main --verbose
python -m src.main --profile high_performance
python -m src.main --list-devices
```

---

**FIN DES INSTRUCTIONS**

Tu as maintenant toutes les informations nécessaires pour développer cette solution de A à Z. Le résultat final doit être un projet clé en main que l'utilisateur peut installer et utiliser immédiatement pour ses appels professionnels avec ses fournisseurs anglophones.

Bonne chance ! 🚀
