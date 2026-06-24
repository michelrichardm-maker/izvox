#!/usr/bin/env python
"""
Génère le manifest d'intégrité des fichiers source izvox.

À lancer à chaque release pour produire `SOURCES.sha256`. Au démarrage,
izvox peut être lancé avec `--verify-sources` (ou `--paranoid`) pour
recalculer les hashes et refuser de démarrer si un fichier source a été
modifié hors release.

Usage :
    python tools/sign_sources.py                       # → SOURCES.sha256
    python tools/sign_sources.py --output release.sha256
    python tools/sign_sources.py --verify              # vérifie + exit non-zéro si KO
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.security.integrity import (  # noqa: E402
    compute_source_hashes,
    verify_source_integrity,
    write_source_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Génère ou vérifie le manifest d'intégrité des sources."
    )
    parser.add_argument(
        "--output", "-o", type=str, default="SOURCES.sha256",
        help="Fichier manifest à écrire/lire (défaut: SOURCES.sha256).",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Vérifie au lieu de générer. Exit code != 0 si un fichier diffère.",
    )
    parser.add_argument(
        "--strict-extra", action="store_true",
        help="En vérif, refuse les fichiers présents mais absents du manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = ROOT / args.output

    if args.verify:
        result = verify_source_integrity(
            root=ROOT,
            manifest_path=manifest_path,
            allow_extra=not args.strict_extra,
        )
        print(f"📁 Sources vérifiées : {result.total} dans le manifest")
        if result.ok:
            print("✓ Intégrité OK")
            return 0
        if result.mismatched:
            print(f"❌ Fichiers modifiés ({len(result.mismatched)}):")
            for f in result.mismatched:
                print(f"   - {f}")
        if result.missing:
            print(f"❌ Fichiers attendus manquants ({len(result.missing)}):")
            for f in result.missing:
                print(f"   - {f}")
        if result.extra and args.strict_extra:
            print(f"⚠ Fichiers hors manifest ({len(result.extra)}):")
            for f in result.extra:
                print(f"   - {f}")
        return 1

    # Mode génération
    hashes = compute_source_hashes(ROOT)
    write_source_manifest(manifest_path, hashes)
    print(f"✓ Manifest écrit : {manifest_path} ({len(hashes)} fichiers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
