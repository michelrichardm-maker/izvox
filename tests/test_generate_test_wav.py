"""Tests pour tools/generate_test_wav.py.

Ces tests vérifient le squelette du script sans avoir besoin que Piper
soit installé : on cible le chemin "voix absente" qui doit dégrader
gracieusement.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def test_default_sentences_exist():
    """Sanity check : les phrases canoniques sont présentes en FR et EN."""
    import generate_test_wav as g
    assert "fr" in g.DEFAULT_SENTENCES
    assert "en" in g.DEFAULT_SENTENCES
    assert len(g.DEFAULT_SENTENCES["fr"]) > 10
    assert len(g.DEFAULT_SENTENCES["en"]) > 10


def test_help_runs_without_error(capsys, monkeypatch):
    """`--help` doit faire un SystemExit(0) propre."""
    import generate_test_wav as g
    monkeypatch.setattr(sys, "argv", ["generate_test_wav.py", "--help"])
    with pytest.raises(SystemExit) as exc:
        g.parse_args()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Génère un WAV" in out
    assert "--lang" in out


def test_missing_voice_returns_nonzero(tmp_path, monkeypatch, capsys):
    """Si la voix Piper n'est pas téléchargée, le script doit retourner
    un code ≠ 0 et imprimer un message d'aide pointant vers
    download_models.py — pas crasher."""
    import generate_test_wav as g
    monkeypatch.setattr(sys, "argv", [
        "generate_test_wav.py",
        "--text", "Bonjour",
        "--lang", "fr",
        "--output", str(tmp_path / "out.wav"),
        "--model-path", str(tmp_path / "no_models_here"),
    ])
    rc = g.main()
    assert rc != 0
    out = capsys.readouterr().out
    assert "download_models" in out
