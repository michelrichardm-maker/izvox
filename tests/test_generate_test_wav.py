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


# -- Test "réel" qui ne tourne que si la voix Piper FR est disponible -----

PIPER_FR_VOICE = "fr_FR-upmc-medium"
PIPER_FR_ONNX = (
    ROOT / "models" / "piper" / PIPER_FR_VOICE / f"{PIPER_FR_VOICE}.onnx"
)


def _piper_fr_available() -> bool:
    if not PIPER_FR_ONNX.exists():
        return False
    try:
        import piper  # type: ignore  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(
    not _piper_fr_available(),
    reason="Piper FR voice not downloaded",
)
def test_generate_test_wav_real_synthesis(tmp_path):
    """Si la voix FR est dispo, on génère un VRAI WAV et on vérifie qu'il
    est lisible (mono int16, durée > 0)."""
    import generate_test_wav as g

    output = tmp_path / "real.wav"
    rc = g._synthesize_one(
        lang="fr",
        text="Bonjour, ceci est un test de synthèse vocale.",
        output=output,
        model_path=str(ROOT / "models" / "piper"),
    )
    assert rc == 0
    assert output.exists()

    import soundfile as sf
    data, sr = sf.read(str(output), dtype="int16")
    # Au moins 0.3s d'audio
    assert sr in (16000, 22050), f"sample-rate inattendu: {sr}"
    assert data.size > sr * 0.3, f"WAV trop court: {data.size} samples"
