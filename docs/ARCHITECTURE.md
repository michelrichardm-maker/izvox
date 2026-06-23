# 🏗️ Architecture technique

## Vue d'ensemble

izvox orchestre **deux pipelines parallèles** (outgoing et incoming) qui
s'exécutent en `asyncio.gather` :

```
┌─────────────────────────────────────────────────────────────────────┐
│                       BilingualTranslator                            │
│  ┌────────────────────┐         ┌────────────────────┐               │
│  │ Outgoing Pipeline  │         │ Incoming Pipeline  │               │
│  │  (Micro → CABLE)   │         │ (CABLE-B → 🔊)     │               │
│  │  FR → EN           │         │ EN → FR            │               │
│  └────────────────────┘         └────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

## Flux OUTGOING (vous → interlocuteur)

```
🎤 Micro physique
   │  (PyAudioWPatch — 16 kHz, mono, int16)
   ▼
┌──────────────┐
│ Silero VAD   │ ← Filtre les silences
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Faster-Whisper│ ← Audio FR → texte FR
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ NLLB-200     │ ← Texte FR → texte EN
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Piper TTS    │ ← Texte EN → audio EN
└──────┬───────┘
       │
       ▼
🔌 CABLE Input (VB-Audio)
       │
       ▼
💻 Teams (configuré : micro = CABLE Input)
       │
       ▼
🌐 Interlocuteur entend ANGLAIS
```

## Flux INCOMING (interlocuteur → vous)

```
🌐 Interlocuteur parle ANGLAIS
       │
       ▼
💻 Teams (configuré : sortie = CABLE-B Input)
       │
       ▼
🔌 CABLE-B (VB-Audio)
       │  (Loopback WASAPI exclusif)
       ▼
┌──────────────┐
│ Silero VAD   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Faster-Whisper│ ← Audio EN → texte EN
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ NLLB-200     │ ← Texte EN → texte FR
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Piper TTS    │ ← Texte FR → audio FR
└──────┬───────┘
       │
       ▼
🔊 Haut-parleurs (périphérique par défaut)
       │
       ▼
👤 Vous entendez FRANÇAIS
```

## Modules

### `src/config.py`
Toutes les dataclasses de configuration. Sérialisation YAML.

### `src/hardware_detector.py`
Détecte CPU, RAM, GPU NVIDIA (CUDA), GPU DirectML. Détermine le
`HardwareLevel` (HIGH/MEDIUM/LOW/CPU_ONLY).

### `src/model_manager.py`
Mappe `HardwareLevel` → choix des modèles. Télécharge les voix Piper
manquantes. Configure les répertoires de cache.

### `src/audio_manager.py`
Wrapper autour de PyAudioWPatch. Gère :
- Enumération des périphériques
- Recherche par motif de nom
- Ouverture de streams input/output/loopback WASAPI

### `src/vad.py`
Deux implémentations de Voice Activity Detection :
- `SileroVAD` (modèle neural, haute précision)
- `RMSVAD` (énergie, ultra-léger)

### `src/stt.py`
`STTProcessor` accumule des chunks audio dans un buffer et appelle
Faster-Whisper quand la durée minimale est atteinte.

### `src/translator.py`
`TranslatorProcessor` supporte NLLB-200 et Opus-MT (auto-détecté par
le nom de modèle).

### `src/tts.py`
`TTSProcessor` charge la voix Piper appropriée. Streaming PCM int16
à 22050 Hz.

### `src/pipeline.py`
- `TranslationPipeline` : un sens (VAD → STT → Translation → TTS → output)
- `BilingualTranslator` : orchestre les deux pipelines via `asyncio`

### `src/main.py`
CLI argparse + boucle asyncio + gestion des signaux.

## Modèle de concurrence

Les deux pipelines tournent dans la même boucle `asyncio`. Les appels
bloquants (lecture audio, inférence GPU, écriture audio) sont délégués
au `default_executor` via `run_in_executor`.

Cela évite que l'inférence d'un sens bloque l'autre. Le GIL Python n'est
pas un problème car les wait audio et les inférences GPU libèrent le GIL.

## Latence cible

| Composant      | Latence (profil balanced, RTX 2060) |
|----------------|-------------------------------------|
| Audio capture  | ~64 ms (1 chunk de 1024 samples)    |
| Silero VAD     | ~5 ms                               |
| Whisper medium | ~200 ms                             |
| NLLB-1.3B      | ~250 ms                             |
| Piper medium   | ~150 ms                             |
| **Total**      | **~670 ms**                         |

## Choix techniques

### Pourquoi Faster-Whisper plutôt qu'OpenAI Whisper ?
- 4 à 5x plus rapide grâce à CTranslate2
- Support natif int8 et float16
- Même qualité

### Pourquoi NLLB-200 plutôt que Marian/Opus-MT ?
- Qualité bien supérieure pour les phrases complexes
- Multi-langue dans un seul modèle
- Fallback Opus-MT en mode CPU (plus léger)

### Pourquoi Piper TTS plutôt que Coqui/Tortoise ?
- Streaming temps réel
- ONNX = pas de PyTorch nécessaire
- Voix de qualité acceptable en local

### Pourquoi VB-Cable plutôt que VoiceMeeter ?
- VoiceMeeter est plus complet mais plus complexe à configurer
- VB-Cable suffit pour notre usage
- A+B nous donne deux câbles indépendants
