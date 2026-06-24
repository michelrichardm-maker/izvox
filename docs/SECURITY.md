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

## Palier 2 — Defense in depth

Le Palier 2 ajoute des contrôles à exposition réduite (best-effort sur OS
non privilégié) et de l'auditabilité post-incident.

### Memory locking & scrub

| Flag | Effet |
|------|-------|
| `--lock-memory` | Tente `mlockall(MCL_CURRENT \| MCL_FUTURE)` (Linux/macOS) ou `SetProcessWorkingSetSize` (Windows). Échec silencieux si pas de privilège. |
| (automatique) | `STTProcessor.audio_buffer` est un `SecureAudioBuffer` qui overwrite chaque chunk numpy avec des zéros avant de libérer la référence. |

Ces contrôles réduisent la fenêtre d'exposition d'un dump mémoire ou d'un
résidu de swap. Ils ne sont **pas une garantie hard** : Python peut
reallouer ailleurs, le GC peut conserver des copies. C'est une bonne
hygiène, pas une promesse.

### Audit log hash-chainé

```powershell
python -m src.main --audit-log logs/audit.jsonl
```

Chaque événement (startup, model_loaded, network_lockdown, models_ready,
shutdown, error) est écrit en JSONL avec :
- `seq`: numéro séquentiel
- `ts`: timestamp ISO8601
- `event`: type
- `data`: métadonnées (jamais de contenu textuel)
- `prev_hash`: hash de l'événement précédent
- `hash`: SHA-256 de cet événement chaîné

Vérification post-mortem :
```python
from src.security.audit import verify_audit_log
result = verify_audit_log("logs/audit.jsonl")
assert result.ok, result.reason
```

**Limite** : tamper-evident, pas tamper-proof. Un attaquant qui contrôle
le fichier peut réécrire toute la chaîne de zéro. Pour rendre ça
infalsifiable : checkpointer le `last_hash` ailleurs (Slack, e-mail) OU
HMAC avec un secret externe → roadmap Tier 3.

### Source integrity manifest

```bash
# Au moment de la release, on signe les sources :
python tools/sign_sources.py
git add SOURCES.sha256 && git commit -m "Sign sources for vX"

# Au runtime, on vérifie :
python -m src.main --verify-sources
```

Génère / vérifie `SOURCES.sha256` au format standard sha256sum. Couvre
tous les `.py`, `.yaml`, `.toml`, `.json`, `.md` sous `src/`, `tests/`,
`tools/`, `config/`, `scripts/`, `docs/` + fichiers racine. Si un fichier
est modifié hors release, izvox refuse de démarrer en mode `--paranoid`.

**Limite** : sans signature externe (cosign), un attaquant peut aussi
regénérer le manifest. C'est de la détection de tampering opportuniste,
pas une chaîne de confiance complète → roadmap Tier 3.

### SBOM CycloneDX

Généré en CI pour chaque push sur `main` et uploadé comme artefact
GitHub Actions (90 jours de rétention) :

```bash
python tools/generate_sbom.py --output sbom.json
python tools/generate_sbom.py --output sbom.xml --format xml
```

Utilise `cyclonedx-bom` si présent (SBOM conforme CycloneDX 1.5), sinon
fallback minimal sur `pip list`. Utile pour répondre rapidement à une
CVE (chercher version vulnérable dans toutes les releases) et pour
audits supply-chain.

### Récap des flags Palier 2

| Flag | Active |
|------|--------|
| `--lock-memory` | Verrouillage mémoire best-effort |
| `--verify-sources` | Vérifie `SOURCES.sha256` au démarrage |
| `--audit-log FILE` | Active le journal hash-chainé |
| `--paranoid` (étendu) | Tous les flags ci-dessus + tous ceux du Palier 1 |

## Roadmap Palier 3

- **Élimination de VB-Cable** : capture WASAPI session-level direct sur
  le process Teams (Windows 10 1903+). Plus de câble multi-tenant.
- **AppContainer Windows** : sandboxing avec capacités réduites
- **Docker reproductible** : image distroless avec deps hashées
- **Signature Cosign** : signe `SOURCES.sha256` + SBOM + release tarball.
  Permet une vérification *réelle* hors-bande, et non plus seulement
  opportuniste.
- **HMAC sur audit log** : secret persistant côté TPM ou DPAPI pour rendre
  le log tamper-proof, pas juste tamper-evident.

## Signaler une faille

Ne pas ouvrir d'issue publique. Email : `security@<votre-domaine>`
(remplacer avant publication).
