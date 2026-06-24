"""
Point d'entrée principal de l'application izvox.

Usage:
    python -m src.main [options]

Options principales:
    --config FILE      Charge la configuration depuis un fichier YAML
    --profile NAME     Force un profil (high_performance/balanced/low_resource/cpu_only)
    --verbose          Active le mode verbeux
    --log-file FILE    Écrit les logs dans un fichier
    --list-devices     Affiche les périphériques audio et quitte
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from .config import AppConfig
from .model_manager import ModelManager
from .pipeline import BilingualTranslator
from .utils import print_banner, setup_logging


def parse_args() -> argparse.Namespace:
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        prog="izvox",
        description=(
            "Traducteur bidirectionnel temps réel (FR↔EN) "
            "pour Teams/Zoom/Meet sous Windows."
        ),
    )

    parser.add_argument(
        "--config", "-c",
        type=str, default=None,
        help="Fichier de configuration YAML",
    )
    parser.add_argument(
        "--profile", "-p",
        type=str,
        choices=["high_performance", "balanced", "low_resource", "cpu_only"],
        default=None,
        help="Profil de performance (surcharge la détection auto)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux (DEBUG)",
    )
    parser.add_argument(
        "--log-file",
        type=str, default=None,
        help="Fichier de log",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Liste les périphériques audio et quitte",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="N'affiche pas la bannière de démarrage",
    )

    # Zero-trust / confidentialité
    sec_group = parser.add_argument_group("Zero-trust / confidentialité")
    sec_group.add_argument(
        "--no-redact", action="store_true",
        help="Affiche le contenu textuel des transcripts dans les logs "
             "(par défaut masqué).",
    )
    sec_group.add_argument(
        "--in-memory", action="store_true",
        help="Refuse tout écriture disque (logs fichier, WAV input/output).",
    )
    sec_group.add_argument(
        "--no-network", action="store_true",
        help="Bloque toute connexion non-loopback après chargement des modèles.",
    )
    sec_group.add_argument(
        "--strict-models", action="store_true",
        help="Refuse de charger les modèles non listés dans models/manifest.json.",
    )
    sec_group.add_argument(
        "--lock-memory", action="store_true",
        help="Empêche le swap des pages du process (best-effort, peut "
             "échouer sans privilège).",
    )
    sec_group.add_argument(
        "--verify-sources", action="store_true",
        help="Vérifie le manifest SOURCES.sha256 au démarrage. Refuse de "
             "démarrer si un fichier source a été modifié.",
    )
    sec_group.add_argument(
        "--audit-log", type=str, default=None,
        help="Active le journal d'audit hash-chainé vers le fichier indiqué "
             "(format JSONL).",
    )
    sec_group.add_argument(
        "--paranoid", action="store_true",
        help="Active tous les contrôles ci-dessus + log_level WARNING.",
    )

    # Mode fichier WAV : permet de tester le pipeline sans matériel audio
    file_group = parser.add_argument_group("Mode fichier WAV (dev/test)")
    file_group.add_argument(
        "--input-file",
        type=str, default=None,
        help="WAV d'entrée (n'importe quel sample-rate, mono/stéréo)",
    )
    file_group.add_argument(
        "--output-file",
        type=str, default=None,
        help="WAV de sortie (généré par TTS)",
    )
    file_group.add_argument(
        "--source-lang",
        type=str, default="fr",
        help="Langue source en mode fichier (défaut: fr)",
    )
    file_group.add_argument(
        "--target-lang",
        type=str, default="en",
        help="Langue cible en mode fichier (défaut: en)",
    )

    return parser.parse_args()


async def main() -> None:
    """Fonction principale async."""
    args = parse_args()

    # Fix Bug #3 : --paranoid et --no-redact sont contradictoires. On rejette
    # explicitement plutôt que de laisser l'un gagner silencieusement.
    if args.paranoid and args.no_redact:
        print(
            "❌ --paranoid et --no-redact sont contradictoires.",
            file=sys.stderr,
        )
        sys.exit(2)

    # --paranoid implique tous les contrôles + log_level WARNING.
    if args.paranoid:
        args.no_network = True
        args.in_memory = True
        args.strict_models = True
        args.lock_memory = True
        args.verify_sources = True

    # --in-memory interdit les écritures disque non-essentielles
    if args.in_memory:
        if args.log_file:
            print(
                "❌ --in-memory et --log-file sont incompatibles "
                "(les logs vers fichier sont une fuite disque).",
                file=sys.stderr,
            )
            sys.exit(2)
        if args.output_file:
            print(
                "❌ --in-memory interdit --output-file (création de fichier disque).",
                file=sys.stderr,
            )
            sys.exit(2)
        # Fix Bug #4 : --audit-log écrit un journal JSONL sur disque, donc
        # incompatible avec --in-memory. On rejette pour ne pas violer
        # silencieusement le contrat "aucun artefact disque".
        if args.audit_log:
            print(
                "❌ --in-memory interdit --audit-log (le journal est un "
                "artefact disque). Utilisez un audit log en mémoire seulement "
                "via l'API Python (AuditLog(path=None)) si nécessaire.",
                file=sys.stderr,
            )
            sys.exit(2)

    if args.paranoid:
        log_level = "WARNING"
    elif args.verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    setup_logging(level=log_level, log_file=args.log_file)
    logger = logging.getLogger("izvox")

    if not args.no_banner:
        print_banner()

    # Source integrity (avant tout, pour ne pas exécuter un izvox altéré)
    if args.verify_sources:
        from pathlib import Path as _Path
        from .security.integrity import verify_source_integrity
        sources_manifest = _Path("SOURCES.sha256")
        if not sources_manifest.exists():
            logger.error(
                "❌ --verify-sources demandé mais SOURCES.sha256 absent. "
                "Lancez `python tools/sign_sources.py` pour le générer."
            )
            sys.exit(2)
        result = verify_source_integrity(_Path("."), sources_manifest)
        if not result.ok:
            logger.error(
                f"❌ Intégrité des sources compromise : "
                f"{len(result.mismatched)} fichiers modifiés, "
                f"{len(result.missing)} manquants."
            )
            for f in result.mismatched:
                logger.error(f"   modifié: {f}")
            for f in result.missing:
                logger.error(f"   absent : {f}")
            sys.exit(3)
        logger.info(f"✓ Intégrité sources OK ({result.total} fichiers vérifiés)")

    # Memory locking (avant chargement des modèles pour couvrir aussi
    # leurs allocations futures)
    if args.lock_memory:
        from .security import lock_process_memory
        lock_process_memory()

    # Audit log
    audit = None
    if args.audit_log:
        from .security import AuditLog
        audit = AuditLog(args.audit_log)
        audit.append("startup", {
            "version": "2.0.0",
            "paranoid": args.paranoid,
            "in_memory": args.in_memory,
            "no_network": args.no_network,
            "strict_models": args.strict_models,
            "lock_memory": args.lock_memory,
        })

    if args.list_devices:
        from .audio_manager import AudioManager
        manager = AudioManager()
        manager.print_devices()
        manager.close_all()
        return

    if args.config and Path(args.config).exists():
        config = AppConfig.from_yaml(args.config)
        logger.info(f"Configuration chargée: {args.config}")
    else:
        config = AppConfig()

    # Propage les flags zero-trust à la config (la config YAML peut aussi les
    # définir ; la ligne de commande surcharge si présente).
    if args.no_redact:
        config.redact_logs = False
    if args.in_memory:
        config.in_memory_only = True
    if args.no_network:
        config.network_lockdown = True
    if args.strict_models:
        config.strict_models = True

    # Fix Bug #3 : --paranoid doit FORCER tous les contrôles, même si le YAML
    # dit l'inverse. Sans cette ligne, `redact_logs: false` dans la config
    # désactivait silencieusement la redaction en mode paranoïaque.
    if args.paranoid:
        config.redact_logs = True
        config.in_memory_only = True
        config.network_lockdown = True
        config.strict_models = True

    # Fix Bug #2 : appliquer le profil utilisateur AVANT ModelManager.
    # Sans ça, l'auto-détection sélectionne ses propres modèles, on les
    # télécharge/charge, puis args.profile change juste les strings de
    # config sans effet runtime.
    user_forced_profile = bool(args.profile)
    if user_forced_profile:
        config.apply_profile(args.profile)
        logger.info(f"Profil forcé (avant init): {args.profile}")

    try:
        model_manager = ModelManager(
            config,
            # Si l'utilisateur a forcé un profil, on désactive l'auto-détection
            # matérielle qui sinon écraserait son choix.
            auto_detect=not user_forced_profile,
            strict_models=config.strict_models,
        )
        model_manager.initialize(verbose=True)
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Erreur initialisation: {e}")
        sys.exit(1)

    # Lockdown egress APRÈS chargement des modèles (qui peut télécharger).
    if config.network_lockdown:
        from .security import lockdown_egress
        lockdown_egress()
        if audit:
            audit.append("network_lockdown", {})

    if audit:
        audit.append("models_ready", {
            "stt": config.stt.model_size,
            "translation": config.translation.model_name,
            "vad": config.vad.backend,
        })

    # Mode fichier : court-circuite tout l'audio device et le double pipeline
    if args.input_file:
        if not args.output_file:
            logger.error("--output-file est requis quand --input-file est utilisé")
            sys.exit(2)
        from .file_pipeline import FilePipeline
        file_pipeline = FilePipeline(
            config=config,
            input_file=args.input_file,
            output_file=args.output_file,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
        )
        try:
            result = await file_pipeline.run()
            logger.info(
                f"✓ Mode fichier terminé : {len(result.transcripts)} phrases, "
                f"{result.total_processing_time_s:.1f}s de traitement pour "
                f"{result.total_audio_duration_s:.1f}s d'audio "
                f"(ratio {result.total_processing_time_s / max(result.total_audio_duration_s, 0.001):.2f}x)"
            )
            if audit:
                audit.append("file_pipeline_done", {
                    "transcripts": len(result.transcripts),
                    "audio_s": result.total_audio_duration_s,
                    "processing_s": result.total_processing_time_s,
                })
                audit.append("shutdown", {})
                audit.close()
            return
        except Exception as e:  # noqa: BLE001
            logger.error(f"❌ Erreur mode fichier: {e}", exc_info=True)
            if audit:
                audit.append("error", {"phase": "file_pipeline"})
                audit.close()
            sys.exit(1)

    translator = BilingualTranslator(config)

    stop_event = asyncio.Event()

    def signal_handler(*_args) -> None:
        logger.info("\n⚠️ Signal d'interruption reçu")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        translator_task = asyncio.create_task(translator.start())
        stop_task = asyncio.create_task(stop_event.wait())
        done, _pending = await asyncio.wait(
            {translator_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task in done:
            await translator.stop()
            translator_task.cancel()
            try:
                await translator_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
    except KeyboardInterrupt:
        await translator.stop()
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        if audit:
            audit.append("error", {"phase": "runtime"})
        await translator.stop()
        if audit:
            audit.append("shutdown", {"exit_code": 1})
            audit.close()
        sys.exit(1)
    finally:
        if audit:
            try:
                audit.append("shutdown", {"exit_code": 0, "stats": translator.get_stats()})
            except Exception:  # noqa: BLE001
                audit.append("shutdown", {"exit_code": 0})
            audit.close()


def run() -> None:
    """Point d'entrée pour le script console."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
