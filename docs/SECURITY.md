# 🔒 Sécurité et confidentialité izvox

## Modèle de menace

izvox est conçu pour des appels professionnels où la conversation est
**confidentielle**. Cette doc explique ce que izvox protège, ce qu'il ne
protège pas, et comment durcir la configuration.

### Ce qui est protégé par design

- ✅ **Aucun appel cloud** : tout tourne en local, pas de transit chez OpenAI,
  Azure, Google, etc.
- ✅ **Pas de télémétrie**
- ✅ **Code open source** (audit possible)
- ✅ **Modèles open source** (Whisper, NLLB, Piper, Silero VAD)

### Menaces couvertes par le Palier 1 (zero-trust)

| Menace | Contrôle | Activation |
|--------|----------|------------|
| Logs disque révèlent les transcriptions | **Redaction** (`maybe_redact`) | Défaut ON |
| Logs écrits via `--log-file` | **No-disk mode** (`--in-memory`) | Opt-in |
| Modèle backdooré injecté dans `models/` | **Hash pinning** (`models/manifest.json`) | Défaut warn, `--strict-models` pour bloquer |
| Modèle ML phone home après init | **Egress lockdown** (`--no-network`) | Opt-in |
| Combinaison de tous les contrôles | `--paranoid` | Opt-in |

### Menaces NON couvertes

| Menace | Statut | Mitigation possible |
|--------|--------|---------------------|
| Malware OS-level / EDR backdooré | ❌ Hors périmètre | Sécuriser l'OS, EDR de confiance |
| Keylogger qui lit le micro avant izvox | ❌ Hors périmètre | OS hardening |
| **VB-Cable multi-tenant** (autre process écoute) | ⚠️ Risque réel | Voir Palier 3 |
| Accès physique à la machine | ❌ Hors périmètre | Chiffrement disque |
| Forensics mémoire si crash dump | ⚠️ | Voir Palier 2 (memory locking + scrub) |

## Contrôles activés par défaut

Sans aucun flag, izvox déjà :
- Masque le contenu textuel dans les logs (`redact_logs = true`)
- Vérifie les hashes des voix Piper après téléchargement (mode non-strict :
  warning si un artefact n'est pas dans le manifest)

## Mode paranoïaque

```powershell
python -m src.main --paranoid
```

`--paranoid` active :
- `--no-network` : bloque toute connexion non-loopback après init
- `--in-memory` : refuse `--log-file` et `--output-file`
- `--strict-models` : refuse de charger un artefact non listé dans
  `models/manifest.json`
- `log_level = WARNING` : pas même de logs INFO contenant des indices
- redact (déjà par défaut)

## Contrôles individuels

| Flag | Effet |
|------|-------|
| `--no-redact` | Logs INFO contiennent le texte clair (utile pour debug local) |
| `--in-memory` | Échoue si `--log-file` ou `--output-file` est aussi présent |
| `--no-network` | Monkey-patche `socket.connect` après chargement des modèles |
| `--strict-models` | `ModelManager` refuse les artefacts non listés dans le manifest |
| `--paranoid` | Combine les quatre |

## Manifest et intégrité

Le fichier `models/manifest.json` liste les SHA-256 des fichiers téléchargés
par izvox lui-même (voix Piper). À chaque démarrage :

1. izvox calcule le SHA-256 des fichiers présents.
2. Si un fichier ne matche pas, il est **supprimé** et izvox refuse de
   démarrer. L'utilisateur relance pour re-download propre.
3. En mode `--strict-models`, izvox refuse aussi tout fichier *absent* du
   manifest (pour éviter qu'on glisse une voix de plus en douce).

### Ajouter un artefact au manifest

```bash
sha256sum models/piper/<voice>/<voice>.onnx
# Copier la valeur dans models/manifest.json sous artifacts.<relpath>.sha256
```

### Pourquoi Whisper et NLLB ne sont pas dans le manifest

Ils sont téléchargés par `faster-whisper` et `huggingface_hub`, qui
vérifient déjà leurs propres hashes via les snapshots HF (chaque blob est
identifié par son SHA dans le store local). On évite la double-vérif.

## Egress lockdown

```python
from src.security import lockdown_egress
lockdown_egress()
# Toute connexion non-loopback échoue désormais avec NetworkLockdownError
```

Patche `socket.socket.connect` et `socket.create_connection`. Autorise :
- `127.0.0.0/8`, `::1` (loopback)
- `localhost` (via DNS standard)

Bloque tout le reste (HuggingFace, GitHub, DNS public).

### Limites du lockdown

- Ne couvre PAS les binaires natifs (CTranslate2, ONNX Runtime). En
  pratique, ils n'ouvrent pas de réseau après chargement.
- Ne couvre PAS les processus enfants (os.fork hérite mais
  l'enfant peut re-patcher).
- Process-local : ne survit pas à un `exec()`.

## Audit du runtime

Pour vérifier ce que izvox fait :

```powershell
# Sous Windows : Process Monitor (SysInternals) en filtre par process
# OR
python -m src.main --verbose       # logs DEBUG (mais expose les transcripts)
python -m src.main --no-redact     # logs INFO complets
```

En production confidentielle, ne **jamais** combiner `--verbose` et un
contexte où les logs peuvent fuiter (CI, sauvegardes, support).

## Roadmap (Paliers 2 et 3)

Cette doc couvre le Palier 1. Voir la conversation/issues pour :

- **Palier 2** : memory locking, scrub, audit hash-chainé, integrity
  manifest des sources, deps hashées, SBOM
- **Palier 3** : AppContainer Windows, élimination de VB-Cable au profit
  d'un loopback session-level, Docker reproductible, signature Cosign

## Signaler une faille

Ne pas ouvrir d'issue publique. Email : `security@<votre-domaine>`
(remplacer avant publication).
