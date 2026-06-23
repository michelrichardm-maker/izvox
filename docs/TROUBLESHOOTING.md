# 🆘 Dépannage

## Erreurs d'installation

### `python n'est pas reconnu`
Python n'est pas dans le PATH. Réinstallez en cochant **"Add Python to PATH"**.

### `pip install torch` échoue avec timeout
Téléchargement très long. Utilisez :
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --timeout 600
```

### `Could not find pyaudiowpatch`
PyAudioWPatch n'est disponible que sur Windows. Sur Linux/macOS, izvox
ne fonctionne pas tel quel (le loopback WASAPI est Windows-only).

## Erreurs au démarrage

### `AudioDeviceNotFoundError: 'CABLE Input' non trouvé`
- Installez VB-Audio Virtual Cable, voir `scripts/setup_vbcable.md`
- Redémarrez Windows
- Vérifiez avec `python tools\audio_diagnostic.py`

### `AudioDeviceNotFoundError: Loopback 'CABLE-B' non trouvé`
- Vous avez installé seulement VB-CABLE, pas VB-CABLE A+B
- Téléchargez le pack A+B sur <https://vb-audio.com/Cable/>

### `ModelNotFoundError: Voix Piper non trouvée`
```powershell
python tools\download_models.py --piper-only
```

### `CUDA out of memory`
Votre GPU est trop petit pour le profil détecté. Forcez un profil plus léger :
```powershell
python -m src.main --profile low_resource
```

### `torch.cuda.is_available()` retourne False
- Vérifiez que vous avez installé la version CUDA de PyTorch :
  ```powershell
  python -c "import torch; print(torch.version.cuda)"
  ```
- Doit afficher `11.8` (ou similaire), pas `None`
- Sinon : `pip uninstall torch && pip install torch --index-url https://download.pytorch.org/whl/cu118`

## Problèmes audio

### L'interlocuteur n'entend rien
- Vérifiez le micro choisi dans Teams : doit être **CABLE Input**
- izvox doit afficher des lignes `[outgoing] 📝 FR: …` quand vous parlez
- Si rien ne s'affiche : ajustez `audio.vad_threshold` (descendez à 0.005)

### Je n'entends pas la traduction
- Vérifiez la sortie haut-parleur Teams : doit être **CABLE-B Input**
- Sur Windows, vérifiez le périphérique de sortie système par défaut
- Si izvox affiche `[incoming] 🔄 FR: …` mais pas de son : problème de
  routage audio

### Echo / larsen
- Désactivez les améliorations audio Windows (clic droit sur le périph. →
  Propriétés → Améliorations → cocher "Désactiver toutes les améliorations")
- Utilisez un casque-micro plutôt qu'un micro ambiant

### Audio haché
- Augmentez `audio.chunk_size` à 2048 ou 4096
- Désactivez les processus gourmands (ne lancez pas Whisper large-v3
  sur un laptop sur batterie)

## Latence

### Latence trop élevée
1. Forcez un profil plus léger : `--profile low_resource`
2. Vérifiez que vous êtes bien sur GPU (`python tools\benchmark.py`)
3. Réduisez `stt.beam_size` à 1
4. Réduisez `translation.num_beams` à 1
5. Utilisez `compute_type: int8` plutôt que `float16`

### Réactivité lente (la phrase met du temps à être traitée)
- Réduisez `vad.min_silence_duration` à 0.3
- Réduisez `audio.silence_duration` à 0.3

## Qualité de la traduction

### Traductions étranges
- Préférez le profil `high_performance` (NLLB-3.3B est nettement meilleur)
- Vérifiez la qualité de la transcription Whisper — si elle est mauvaise,
  la traduction le sera aussi (garbage in, garbage out)

### Whisper transcrit n'importe quoi
- Vérifiez que `stt.language` est bien `fr` côté outgoing
- Bruit ambiant trop fort : utilisez un meilleur micro

## FAQ

### Puis-je l'utiliser pour d'autres langues ?
Oui, NLLB-200 supporte 200 langues. Modifiez `stt.language` et les codes
NLLB dans le pipeline (ex. `spa_Latn` pour espagnol).

### Est-ce que ça marche hors-ligne ?
Après le premier téléchargement des modèles, oui — 100 % offline.

### Mes données sont-elles envoyées quelque part ?
Non. Tout reste en local sur votre machine.

### Compatible Mac/Linux ?
Pas tel quel. Le loopback WASAPI est spécifique à Windows. Sur Linux,
PulseAudio peut faire l'équivalent mais demande une adaptation du code.

### Combien ça coûte ?
$0 en runtime. Vous payez juste l'électricité de votre GPU.
