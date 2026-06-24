#!/usr/bin/env python
"""
Génère un Software Bill of Materials (SBOM) au format CycloneDX.

Le SBOM liste toutes les dépendances pip installées dans l'environnement
courant avec leurs versions et leurs hashes. Utile pour :
- Audits supply-chain (savoir exactement quoi a été installé)
- Réponse rapide à une CVE (chercher "library X version Y" dans tous les
  SBOMs des releases)
- Reproductibilité

Usage :
    python tools/generate_sbom.py                      # → sbom.json
    python tools/generate_sbom.py --output izvox.cdx.json
    python tools/generate_sbom.py --format xml         # CycloneDX XML

Utilise `cyclonedx-bom` (paquet `cyclonedx-bom` sur PyPI). Si absent,
fallback minimal sur `pip list --format=json` pour produire un SBOM
basique (non-conforme CycloneDX strict mais utilisable).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Génère un SBOM CycloneDX de l'environnement izvox.",
    )
    parser.add_argument(
        "--output", "-o", type=str, default="sbom.json",
        help="Fichier de sortie (défaut: sbom.json).",
    )
    parser.add_argument(
        "--format", "-f", choices=["json", "xml"], default="json",
        help="Format de sortie CycloneDX.",
    )
    return parser.parse_args()


def _try_cyclonedx(output: Path, fmt: str) -> bool:
    """Essaie `cyclonedx-py environment`. Renvoie True si succès."""
    try:
        # cyclonedx-bom >= 4.x (commande `cyclonedx-py`)
        cmd = [
            sys.executable, "-m", "cyclonedx_py", "environment",
            "--output-format", fmt,
            "--output-file", str(output),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0 and output.exists():
            return True
        print(f"⚠ cyclonedx-py a échoué (rc={result.returncode}): {result.stderr.strip()}")
    except FileNotFoundError:
        pass
    return False


def _fallback_basic(output: Path) -> None:
    """SBOM minimal via `pip list --format=json` (non-conforme CycloneDX
    strict mais structurellement compatible)."""
    print("📦 Fallback : génération SBOM basique via pip list")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True, text=True, check=True,
    )
    packages = json.loads(result.stdout)
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "tools": [{"vendor": "izvox", "name": "generate_sbom.py", "version": "0.1"}],
            "note": "Fallback SBOM (pip list). For a fully-conforming SBOM, install cyclonedx-bom.",
        },
        "components": [
            {
                "type": "library",
                "name": pkg["name"],
                "version": pkg["version"],
                "purl": f"pkg:pypi/{pkg['name']}@{pkg['version']}",
            }
            for pkg in packages
        ],
    }
    output.write_text(json.dumps(sbom, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Génération du SBOM ({args.format}) → {output}")
    if not _try_cyclonedx(output, args.format):
        if args.format == "xml":
            print("❌ Format XML indisponible sans cyclonedx-bom installé.")
            return 1
        _fallback_basic(output)

    size = output.stat().st_size
    print(f"✓ SBOM écrit : {output} ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
