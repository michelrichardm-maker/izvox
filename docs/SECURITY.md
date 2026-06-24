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

## Palier 3 — Trust roots & sandboxing

### WASAPI exclusive mode (anti multi-tenant CABLE-B)

```yaml
audio:
  loopback_exclusive: true
```

Ouvre le périphérique de loopback en mode WASAPI exclusif : une seule
application peut y accéder. Empêche un autre process malveillant ou
EDR de capturer simultanément l'audio Teams via CABLE-B. Si le driver
refuse l'exclusif, fallback automatique en partagé avec warning.

> **Limite** : ça empêche le sniff par d'autres apps Windows, mais ne
> protège pas contre un attaquant qui prendrait CABLE-B en exclusif
> AVANT izvox. Au démarrage, vérifier que izvox a bien obtenu l'exclusif.

### HMAC audit log (tamper-proof, pas juste evident)

```powershell
$env:IZVOX_AUDIT_KEY = "un-secret-aléatoire-d-au-moins-16-chars"
python -m src.main --audit-log logs\audit.jsonl
```

Quand `IZVOX_AUDIT_KEY` est défini (≥16 caractères), chaque événement
est haché avec HMAC-SHA256(secret, payload + prev_hash) au lieu de
SHA-256 simple. Un attaquant qui modifie le fichier ne peut plus
recalculer un hash valide sans connaître le secret.

Vérification : passer le même secret à `verify_audit_log(path, secret=...)`.

> **Limite** : si le secret traîne dans `$env`, il fuit avec n'importe
> quel core dump du process izvox. Pour une vraie root of trust : stocker
> dans le TPM/DPAPI (Windows) ou tpm2-tools (Linux). Stubs prêts dans
> `src/security/audit.py`.

### Process-level WASAPI loopback (élimination de VB-Cable)

**État : stub.** L'API publique est posée dans
`src/audio_process_capture.py` mais l'implémentation COM/ctypes n'est pas
finalisée. Quand elle le sera, le pipeline pourra capturer directement
l'audio Teams sans passer par VB-Cable B :

```yaml
audio:
  incoming_source: process     # au lieu de "vbcable"
  target_process_name: ms-teams
```

L'API Windows utilisée est `ActivateAudioInterfaceAsync` avec
`AUDIOCLIENT_ACTIVATION_PARAMS{ActivationType =
AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK}`. Requiert Windows 10
build 1903+.

> Voir la docstring complète du module pour la roadmap d'implémentation
> (wrapper C++ ou bind comtypes).

### Docker reproductible distroless

```bash
docker build -t izvox:latest .
docker run --rm \
  -v $PWD/samples:/app/samples:ro \
  -v $PWD/out:/app/out \
  izvox:latest \
  --input-file /app/samples/sample_fr.wav \
  --output-file /app/out/en.wav \
  --paranoid
```

Image multi-stage :
- **Builder** : python:3.12-slim (pinné par digest) + espeak-ng + venv
  avec toutes les deps Python.
- **Runtime** : `gcr.io/distroless/python3-debian12:nonroot` (pinné par
  digest). Pas de shell, pas de pip, pas d'apt. Utilisateur non-root.
  Default args : `--paranoid --no-banner`.

> Utile pour : tests/CI, mode fichier WAV, audits de l'image (cosign +
> SBOM). **Pas utilisable pour un vrai appel Teams** : pas d'accès audio
> physique depuis un container Linux.

### AppContainer Windows (sandbox runtime)

```powershell
.\scripts\run_appcontainer.ps1
```

Lance izvox dans un job restreint Windows avec :
- Limites CPU/mémoire
- Token réduit (DesktopRestricted)
- Pas d'accès réseau au niveau du token (en plus du `--no-network` Python)
- `--paranoid` appliqué par défaut

> Le vrai AppContainer (capabilities microphoneCapability,
> internetClient) requiert `CreateAppContainerProfile` via Win32 API,
> non exposé en PowerShell pur. Le script actuel fournit la partie
> Job Object + token. Roadmap : wrapper p/invoke.

### Cosign keyless signing en CI

Workflow `.github/workflows/release.yml` déclenché à chaque tag
`vX.Y.Z` :

1. Génère `SOURCES.sha256`, `sbom.json`, `sbom.xml`, `izvox-vX.tar.gz`
2. Signe chaque artefact via Sigstore Cosign keyless (OIDC GitHub
   Actions, pas de clé privée à gérer)
3. Vérifie immédiatement les signatures
4. Crée une GitHub Release avec tous les fichiers `.sig` + `.cert`

Vérification côté utilisateur :
```bash
cosign verify-blob \
  --certificate SOURCES.sha256.cert \
  --signature SOURCES.sha256.sig \
  --certificate-identity-regexp '^https://github.com/michelrichardm-maker/izvox/' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  SOURCES.sha256
```

> C'est la **vraie** chaîne de confiance : la signature prouve que
> l'artefact vient bien d'un workflow GitHub Actions de ce repo, sans
> qu'il faille faire confiance à une clé manuelle.

## Récap des flags par palier

| Flag | Palier | Effet |
|------|--------|-------|
| (défaut) | T1 | Redaction des logs |
| `--no-redact` | T1 | Affiche le texte clair |
| `--in-memory` | T1 | Refuse les écritures disque |
| `--no-network` | T1 | Lockdown egress non-loopback |
| `--strict-models` | T1 | Refuse les modèles non listés |
| `--lock-memory` | T2 | Verrouillage mémoire best-effort |
| `--verify-sources` | T2 | Vérifie SOURCES.sha256 au démarrage |
| `--audit-log FILE` | T2 | Journal hash-chainé (HMAC si $IZVOX_AUDIT_KEY) |
| `--paranoid` | T1+T2 | Active tout ce qui précède + log level WARNING |
| `audio.loopback_exclusive: true` | T3 | WASAPI exclusif sur CABLE-B |
| `$IZVOX_AUDIT_KEY` (env) | T3 | Bascule audit log en HMAC |
| `docker run izvox:latest` | T3 | Runtime distroless |
| `scripts/run_appcontainer.ps1` | T3 | Sandbox Windows |
| Tag `vX.Y.Z` | T3 | Release signée Cosign |

## Pour aller plus loin (Tier 3.5+)

- Implémentation réelle du process-level WASAPI loopback (wrapper C++)
- Vraie intégration AppContainer via `CreateAppContainerProfile`
- HMAC audit secret stocké en TPM 2.0 (Linux: tpm2-tools, Windows: TBS)
- Reproducible builds bit-à-bit (SOURCE_DATE_EPOCH, etc.)
- Atestation SLSA niveau 3 sur les artefacts CI

## Signaler une faille

Ne pas ouvrir d'issue publique. Email : `security@<votre-domaine>`
(remplacer avant publication).
