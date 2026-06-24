# 🎙️ Guide d'utilisation

## Démarrage

```powershell
.\scripts\run.bat
```

ou en mode développement :

```powershell
.\venv\Scripts\Activate.ps1
python -m src.main
```

## Options en ligne de commande

| Option              | Description                                                  |
|---------------------|--------------------------------------------------------------|
| `--config FILE`     | Charge une config YAML personnalisée                          |
| `--profile NAME`    | Force un profil (`high_performance`, `balanced`, …)           |
| `--verbose`         | Active les logs DEBUG                                         |
| `--log-file FILE`   | Écrit les logs dans un fichier                                |
| `--list-devices`    | Affiche tous les périphériques audio et quitte                |
| `--no-banner`       | Désactive la bannière de démarrage                            |
| `--input-file FILE` | **Mode fichier** : lit un WAV au lieu du micro                 |
| `--output-file FILE`| **Mode fichier** : écrit le WAV traduit                        |
| `--source-lang LG`  | Langue source en mode fichier (défaut: `fr`)                   |
| `--target-lang LG`  | Langue cible en mode fichier (défaut: `en`)                    |

Exemples :

```powershell
python -m src.main --profile high_performance
python -m src.main --config config\custom.yaml --verbose
python -m src.main --log-file logs\session.log
```

## Mode fichier WAV (dev/test sans matériel audio)

Pratique pour valider le pipeline sans Windows, VB-Cable ou Teams. Lit un
WAV (n'importe quel sample-rate, mono ou stéréo), passe par le même
pipeline VAD → STT → traduction → TTS, écrit un WAV de sortie.

```bash
python -m src.main --input-file samples/fr.wav --output-file out_en.wav
python -m src.main --input-file en.wav --output-file fr.wav \
                  --source-lang en --target-lang fr
```

Sortie type :
```
📁 Chargement samples/fr.wav
   → 64000 samples, 4.00s, 16000Hz
📝 FR: Bonjour, comment allez-vous aujourd'hui ?
🔄 EN: Hello, how are you today?
⏱ Latence: 612ms
📁 out_en.wav écrit (1.43s)
✓ Mode fichier terminé : 1 phrases, 0.9s de traitement pour 4.0s d'audio (ratio 0.22x)
```

Ce mode est utilisé en CI pour valider la chaîne complète sans
dépendances Windows.

## Configurer Teams / Zoom / Meet

Avant ou pendant l'appel :

### 1. Microphone (vous → eux)
Dans les paramètres audio de Teams :
- **Périphérique d'entrée du micro** : `CABLE Input (VB-Audio Virtual Cable)`

izvox capte votre micro physique → traduit vers l'anglais → joue dans CABLE
Input → Teams transmet à l'interlocuteur.

### 2. Haut-parleurs (eux → vous)
- **Haut-parleur** : `CABLE-B Input (VB-Audio Cable B)`

izvox capte la sortie Teams (loopback CABLE-B) → traduit vers le français →
joue sur vos vrais haut-parleurs.

## Pendant l'appel

izvox affiche en temps réel les transcriptions et traductions :

```
[outgoing] 📝 FR: Bonjour, comment allez-vous ?
[outgoing] 🔄 EN: Hello, how are you?
[outgoing] ⏱ Latence: 487ms

[incoming] 📝 EN: I'm doing great, thanks. Let's discuss the contract.
[incoming] 🔄 FR: Je vais très bien, merci. Discutons du contrat.
[incoming] ⏱ Latence: 512ms
```

## Arrêt propre

- **Ctrl + C** dans le terminal
- izvox affiche un récapitulatif statistique avant de quitter

## Conseils

- **Parlez clairement** : Whisper est très bon, mais évitez de manger les mots
- **Phrases courtes** : la latence dépend de la longueur de la phrase
- **Vocabulaire technique** : utilisez l'orthographe officielle des marques
- **Bruit ambiant** : un casque-micro améliore drastiquement la transcription
