# ⚙️ Configuration avancée

izvox se configure via un fichier YAML. Les fichiers fournis dans `config/`
servent de base — copiez-les pour créer votre propre version.

## Lancer avec une config personnalisée

```powershell
python -m src.main --config config\custom.yaml
```

## Structure du fichier

```yaml
profile: balanced               # high_performance | balanced | low_resource | cpu_only
hardware_level: medium          # high | medium | low | cpu_only

audio:
  sample_rate: 16000            # Whisper veut 16 kHz
  channels: 1                   # Mono
  chunk_size: 1024              # Samples par chunk (~64ms à 16kHz)
  format: int16
  vad_threshold: 0.015
  silence_duration: 0.5         # Sec. de silence avant fin de phrase
  input_device_pattern: ""      # "" = micro par défaut
  output_device_pattern: ""     # "" = haut-parleurs par défaut
  vbcable_input_pattern: "CABLE Input"
  vbcable_output_pattern: "CABLE-B"

stt:
  model_size: medium            # tiny, base, small, medium, large-v3
  device: cuda                  # cuda, cpu
  compute_type: int8            # float16, int8, float32
  language: fr                  # fr, en, es, de, …
  beam_size: 5                  # Plus = précis mais lent
  vad_filter: true
  download_root: ./models/whisper

translation:
  model_name: facebook/nllb-200-1.3B
  device: cuda
  source_lang: fra_Latn
  target_lang: eng_Latn
  max_length: 512
  num_beams: 5
  cache_dir: ./models/nllb

tts:
  model_path: ./models/piper
  voice_fr: fr_FR-upmc-medium    # ou fr_FR-siwis-medium
  voice_en: en_US-lessac-medium  # ou en_US-amy-medium
  sample_rate: 22050

vad:
  backend: silero                # silero ou rms
  threshold: 0.5                 # Pour silero (probabilité 0-1)
  rms_threshold: 0.015           # Pour rms
  min_speech_duration: 0.1
  min_silence_duration: 0.5
  sample_rate: 16000

verbose: false
log_level: INFO
enable_stats: true
```

## Profils

### high_performance
Whisper large-v3 + NLLB-3.3B + Piper medium. Pour RTX 3060+ avec 12 GB+ VRAM.

### balanced (défaut)
Whisper medium + NLLB-1.3B + Piper medium. RTX 2060/3050.

### low_resource
Whisper small + NLLB-600M. GPU intégré ou ancien.

### cpu_only
Whisper tiny + Opus-MT. Sans GPU. Latence plus élevée mais reste utilisable.

## Personnaliser les voix Piper

```yaml
tts:
  voice_fr: fr_FR-siwis-medium    # alternative féminine
  voice_en: en_US-amy-medium      # alternative féminine
```

Liste des voix disponibles : <https://huggingface.co/rhasspy/piper-voices>

> N'oubliez pas de relancer `python tools\download_models.py --piper-only`
> après avoir changé de voix.

## Forcer un périphérique audio

```yaml
audio:
  input_device_pattern: "Yeti"           # Recherche "Yeti" dans les noms
  output_device_pattern: "Headphones"
```

Le matching est insensible à la casse et accepte des sous-chaînes.
Listez les périphériques disponibles avec :

```powershell
python tools\audio_diagnostic.py
```

## Tuning latence

| Paramètre              | Effet                                          |
|------------------------|------------------------------------------------|
| `stt.beam_size`        | ↓ pour plus rapide, ↑ pour plus précis         |
| `stt.compute_type`     | `int8` plus rapide que `float16`               |
| `translation.num_beams`| ↓ pour plus rapide                             |
| `audio.chunk_size`     | ↓ pour réactivité, ↑ pour stabilité            |
| `vad.min_silence_duration` | ↓ pour réagir vite à la fin de phrase     |
