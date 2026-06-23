# 📘 Référence API

izvox peut être utilisé comme librairie Python. Voici les points d'entrée
principaux.

## Démarrage rapide programmatique

```python
import asyncio
from src.config import AppConfig
from src.model_manager import ModelManager
from src.pipeline import BilingualTranslator


async def main():
    config = AppConfig()
    model_manager = ModelManager(config, auto_detect=True)
    model_manager.initialize()

    translator = BilingualTranslator(config)
    await translator.start()


asyncio.run(main())
```

## `AppConfig`

```python
from src.config import AppConfig

config = AppConfig()
config.apply_profile("high_performance")
config.audio.chunk_size = 2048
config.to_yaml("my_config.yaml")
```

Attributs principaux :
- `audio: AudioConfig`
- `stt: STTConfig`
- `translation: TranslationConfig`
- `tts: TTSConfig`
- `vad: VADConfig`

## `HardwareDetector`

```python
from src.hardware_detector import HardwareDetector

detector = HardwareDetector()
info = detector.detect()
print(info.gpu_name, info.vram_mb, info.level)
```

## `TranslatorProcessor`

```python
from src.config import TranslationConfig
from src.translator import TranslatorProcessor

config = TranslationConfig(
    model_name="facebook/nllb-200-1.3B",
    device="cuda",
)
translator = TranslatorProcessor(config)

text_en = translator.translate("Bonjour", source_lang="fr", target_lang="en")
print(text_en)  # "Hello"
```

Langues supportées (codes NLLB) :
`fr`, `en`, `es`, `de`, `it`, `pt`, `nl`, `pl`, `ru`, `zh`, `ja`, `ko`, `ar`.

## `STTProcessor`

```python
from src.config import STTConfig
from src.stt import STTProcessor

stt = STTProcessor(STTConfig(model_size="medium", device="cuda"))
stt.add_audio(chunk_bytes, sample_rate=16000)
text = stt.transcribe(flush=False)
```

## `TTSProcessor`

```python
from src.config import TTSConfig
from src.tts import TTSProcessor

tts = TTSProcessor(TTSConfig(), language="en")
audio_pcm = tts.synthesize("Hello world")  # int16 PCM bytes
```

## `VADFactory`

```python
from src.vad import VADFactory

vad = VADFactory.create("silero", threshold=0.5, sample_rate=16000)
if vad.is_speech(audio_chunk):
    print("parole détectée")
```

## `AudioManager`

```python
from src.config import AudioConfig
from src.audio_manager import AudioManager

mgr = AudioManager()
mgr.print_devices()

device = mgr.find_device("Yeti", input_only=True)
stream = mgr.open_input_stream(AudioConfig(), device=device)
```

## `BilingualTranslator`

```python
from src.pipeline import BilingualTranslator

trans = BilingualTranslator(config)
await trans.start()
# ...
await trans.stop()
print(trans.get_stats())
```

## Hook sur les transcriptions

Vous pouvez attacher un callback à chaque pipeline :

```python
def on_transcript(source_text, translated_text, latency_ms):
    print(f"{source_text} → {translated_text} ({latency_ms:.0f}ms)")

translator.outgoing.on_transcript = on_transcript
translator.incoming.on_transcript = on_transcript
```

## Exceptions

```python
from src.exceptions import (
    TranslatorError,
    AudioDeviceNotFoundError,
    ModelLoadError,
    ConfigurationError,
)

try:
    ...
except AudioDeviceNotFoundError:
    print("Périphérique audio absent")
except ModelLoadError:
    print("Modèle non chargé")
```
