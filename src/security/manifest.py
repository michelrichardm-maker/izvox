"""
Vérification d'intégrité des modèles via manifest SHA-256.

Le fichier `models/manifest.json` liste, pour chaque artefact que nous
téléchargeons nous-mêmes (typiquement les voix Piper depuis HuggingFace),
le hash attendu. Si un fichier sur disque ne matche pas, on refuse de
charger : potentiel tampering ou corruption.

Format du manifest :
{
  "version": 1,
  "description": "Hashes of izvox-tracked model artifacts",
  "artifacts": {
    "piper/fr_FR-upmc-medium/fr_FR-upmc-medium.onnx": {
      "sha256": "9abb3800c19...",
      "size": 76733615,
      "source": "https://huggingface.co/rhasspy/piper-voices/..."
    }
  }
}

Note : Whisper et NLLB ne sont pas dans le manifest car ils sont gérés
par faster-whisper / huggingface_hub qui vérifient déjà leurs propres
hashes via les snapshots HF. Le manifest couvre les artefacts pour
lesquels nous contrôlons le chemin de téléchargement direct.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ManifestError(Exception):
    """Erreur générique de manifest."""


class ManifestMismatchError(ManifestError):
    """Le hash d'un fichier ne matche pas le manifest."""


class UnknownArtifactError(ManifestError):
    """L'artefact n'est pas listé dans le manifest (mode strict uniquement)."""


@dataclass(frozen=True)
class ArtifactRecord:
    relpath: str
    sha256: str
    size: Optional[int] = None
    source: Optional[str] = None


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Calcule le SHA-256 d'un fichier en streaming (1 MiB par chunk)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manifest_path: Path) -> Dict[str, ArtifactRecord]:
    """Charge un manifest JSON et retourne {relpath -> ArtifactRecord}.

    Retourne un dict vide si le manifest n'existe pas (cas du dev qui
    démarre sans manifest pour la première fois).
    """
    if not manifest_path.exists():
        logger.debug(f"Manifest absent: {manifest_path}")
        return {}

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"Manifest invalide ({manifest_path}): {e}") from e

    artifacts: Dict[str, ArtifactRecord] = {}
    for relpath, info in (data.get("artifacts") or {}).items():
        sha = info.get("sha256")
        if not sha:
            raise ManifestError(
                f"Manifest entry '{relpath}' sans sha256"
            )
        artifacts[relpath] = ArtifactRecord(
            relpath=relpath,
            sha256=sha.lower(),
            size=info.get("size"),
            source=info.get("source"),
        )
    return artifacts


def verify_artifact(
    path: Path,
    expected_sha256: str,
    delete_on_mismatch: bool = True,
) -> None:
    """Vérifie qu'un fichier matche le SHA-256 attendu.

    Args:
        path: Fichier à vérifier.
        expected_sha256: Hash attendu (hex, insensible à la casse).
        delete_on_mismatch: Si True, supprime le fichier en cas de mismatch
            pour forcer un re-download propre.

    Raises:
        ManifestMismatchError: si le hash ne matche pas.
        FileNotFoundError: si le fichier n'existe pas.
    """
    if not path.exists():
        raise FileNotFoundError(f"Fichier à vérifier introuvable: {path}")

    actual = sha256_file(path)
    if actual.lower() != expected_sha256.lower():
        if delete_on_mismatch:
            try:
                path.unlink()
            except OSError:
                pass  # mieux vaut crasher au-dessus que masquer
        raise ManifestMismatchError(
            f"Hash mismatch pour {path.name}: "
            f"attendu {expected_sha256[:16]}…, obtenu {actual[:16]}…"
        )


def verify_artifact_from_manifest(
    file_path: Path,
    relpath: str,
    manifest: Dict[str, ArtifactRecord],
    strict: bool = False,
) -> None:
    """Vérifie `file_path` contre l'entrée `relpath` du manifest.

    Args:
        file_path: Chemin réel sur disque.
        relpath: Clé dans le manifest (chemin relatif depuis models/).
        manifest: Manifest chargé par `load_manifest`.
        strict: Si True, lève UnknownArtifactError quand l'entrée manque.
            Sinon (défaut), log un warning et laisse passer.
    """
    record = manifest.get(relpath)
    if record is None:
        if strict:
            raise UnknownArtifactError(
                f"Artefact '{relpath}' absent du manifest (mode strict)"
            )
        logger.warning(f"⚠ Artefact non manifest : {relpath} (hash non vérifié)")
        return

    verify_artifact(file_path, record.sha256, delete_on_mismatch=True)
    logger.info(f"✓ Hash OK : {relpath}")
