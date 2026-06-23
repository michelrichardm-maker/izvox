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

    return parser.parse_args()


async def main() -> None:
    """Fonction principale async."""
    args = parse_args()

    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level, log_file=args.log_file)
    logger = logging.getLogger("izvox")

    if not args.no_banner:
        print_banner()

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

    try:
        model_manager = ModelManager(config, auto_detect=True)
        model_manager.initialize(verbose=True)

        if args.profile:
            config.apply_profile(args.profile)
            logger.info(f"Profil forcé: {args.profile}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Erreur initialisation: {e}")
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
        await translator.stop()
        sys.exit(1)


def run() -> None:
    """Point d'entrée pour le script console."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
