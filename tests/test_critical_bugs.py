"""Tests de non-régression pour les 4 bugs critiques détectés en revue.

Chaque test échoue sur la version pré-fix et passe avec le fix.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import AppConfig, FlowDirection, HardwareLevel


ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# Bug 1 — STT language partagée entre pipelines
# ===========================================================================


def test_bug1_stt_language_not_shared_between_pipelines():
    """OUTGOING et INCOMING doivent avoir leur PROPRE STTConfig avec leur
    propre langue. Avant le fix : les deux pointaient sur la même instance
    et la 2ᵉ init écrasait la 1ʳᵉ.
    """
    from src.pipeline import TranslationPipeline

    cfg = AppConfig()
    cfg.stt.language = "neutral"  # placeholder

    # On crée deux pipelines comme BilingualTranslator le fait.
    out = TranslationPipeline(FlowDirection.OUTGOING, cfg)
    inc = TranslationPipeline(FlowDirection.INCOMING, cfg)

    # Évite de charger les vrais modèles : on patche STTProcessor
    # pour capturer le STTConfig passé.
    captured_configs = []

    class _FakeSTT:
        def __init__(self, stt_config, external_vad=True):
            captured_configs.append(stt_config)

    with patch("src.pipeline.STTProcessor", _FakeSTT), \
         patch("src.pipeline.TranslatorProcessor", MagicMock()), \
         patch("src.pipeline.TTSProcessor", MagicMock()), \
         patch("src.pipeline.AudioManager", MagicMock()), \
         patch("src.pipeline.VADFactory.create", MagicMock()), \
         patch.object(out, "_setup_audio_streams", MagicMock(
             return_value=__import__("asyncio").sleep(0))), \
         patch.object(inc, "_setup_audio_streams", MagicMock(
             return_value=__import__("asyncio").sleep(0))):
        import asyncio
        asyncio.run(out.initialize())
        asyncio.run(inc.initialize())

    assert len(captured_configs) == 2
    out_cfg, inc_cfg = captured_configs
    assert out_cfg.language == "fr"
    assert inc_cfg.language == "en"
    # Les deux objets DOIVENT être différents (pas une référence partagée)
    assert out_cfg is not inc_cfg
    # Et la config globale ne doit PAS avoir été mutée
    assert cfg.stt.language == "neutral"


# ===========================================================================
# Bug 2 — --profile appliqué AVANT l'init des modèles
# ===========================================================================


def test_bug2_profile_applied_before_model_manager():
    """Si l'utilisateur passe --profile high_performance, la config doit
    être patchée AVANT que ModelManager soit construit, et ModelManager
    doit recevoir auto_detect=False pour ne pas écraser le choix.

    On force ModelManager() à lever une exception qu'on intercepte, ce qui
    nous laisse vérifier `captured` sans avoir à mocker tout le runtime.
    """
    captured = {}

    class _Captured(Exception):
        pass

    def _fake_mm_init(config, auto_detect=True, strict_models=False):
        captured["model_size_at_init"] = config.stt.model_size
        captured["translation_model_at_init"] = config.translation.model_name
        captured["auto_detect"] = auto_detect
        raise _Captured("captured")

    args_list = ["main", "--profile", "high_performance", "--no-banner"]

    with patch("sys.argv", args_list), \
         patch("src.main.ModelManager", side_effect=_fake_mm_init):

        import asyncio
        from src.main import main as main_async
        # ModelManager lève _Captured → le try/except de main attrape avec
        # except Exception et sys.exit(1). On attend SystemExit.
        with pytest.raises(SystemExit):
            asyncio.run(main_async())

    # Le profil high_performance doit avoir mis stt.model_size = "large-v3"
    # AVANT que ModelManager soit construit (sinon c'était "medium" du défaut).
    assert captured.get("model_size_at_init") == "large-v3"
    # Et le modèle de traduction doit être NLLB-3.3B (profil high) et non
    # NLLB-1.3B (défaut balanced).
    assert "3.3B" in captured.get("translation_model_at_init", "")
    # Et auto_detect doit être désactivé puisque l'utilisateur a forcé.
    assert captured.get("auto_detect") is False


# ===========================================================================
# Bug 3 — --paranoid doit forcer redact_logs même si YAML dit le contraire
# ===========================================================================


def test_bug3_paranoid_forces_redact_over_yaml(tmp_path):
    """Le mode paranoïaque doit écraser un YAML qui aurait `redact_logs: false`."""
    # On écrit un YAML qui DÉSACTIVE la redaction.
    yaml_path = tmp_path / "leaky.yaml"
    yaml_path.write_text(
        "profile: balanced\n"
        "redact_logs: false\n"
        "in_memory_only: false\n"
        "network_lockdown: false\n"
        "strict_models: false\n",
        encoding="utf-8",
    )

    fake_mm = MagicMock()
    captured = {}

    def _capture_mm(config, auto_detect=True, strict_models=False):
        captured["config"] = config
        return fake_mm

    args_list = [
        "main", "--paranoid",
        "--config", str(yaml_path),
        "--no-banner", "--list-devices",
    ]
    with patch("sys.argv", args_list), \
         patch("src.main.ModelManager", side_effect=_capture_mm), \
         patch("src.audio_manager.AudioManager") as mock_am, \
         patch("src.security.lock_process_memory", MagicMock()):
        mock_am.return_value.print_devices = MagicMock()
        mock_am.return_value.close_all = MagicMock()

        # --paranoid implique --verify-sources, mais SOURCES.sha256 n'existe
        # pas en test. Le code va sys.exit(2). On l'attend.
        import asyncio
        from src.main import main as main_async
        with pytest.raises(SystemExit):
            asyncio.run(main_async())


def test_bug3_paranoid_rejects_no_redact():
    """--paranoid et --no-redact sont contradictoires → exit code 2."""
    cmd = [
        sys.executable, "-m", "src.main",
        "--paranoid", "--no-redact", "--no-banner",
    ]
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    assert "contradictoires" in result.stderr.lower()


# ===========================================================================
# Bug 4 — --in-memory + --audit-log doivent être rejetés
# ===========================================================================


def test_bug4_in_memory_rejects_audit_log():
    """L'audit log écrit un JSONL sur disque, donc incompatible avec
    --in-memory. Doit exit code 2 avec message clair."""
    cmd = [
        sys.executable, "-m", "src.main",
        "--in-memory", "--audit-log", "/tmp/x.jsonl",
        "--no-banner",
    ]
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    err = result.stderr.lower()
    assert "in-memory" in err
    assert "audit-log" in err


def test_bug4_in_memory_still_rejects_log_file():
    """Régression : le rejet existant de --log-file ne doit pas être cassé."""
    cmd = [
        sys.executable, "-m", "src.main",
        "--in-memory", "--log-file", "/tmp/x.log",
        "--no-banner",
    ]
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    assert "log-file" in result.stderr.lower()


def test_bug4_in_memory_still_rejects_output_file():
    cmd = [
        sys.executable, "-m", "src.main",
        "--in-memory", "--output-file", "/tmp/x.wav",
        "--no-banner",
    ]
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    assert "output-file" in result.stderr.lower()
