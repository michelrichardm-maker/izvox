"""Tests pour le traducteur.

Note: ces tests nécessitent le téléchargement du modèle Opus-MT (~300 MB).
Pour ignorer en local: pytest -m "not slow".
"""

import pytest

from src.config import TranslationConfig

try:
    from src.translator import TranslatorProcessor
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


pytestmark = pytest.mark.skipif(
    not HAS_DEPS, reason="transformers/torch non installés"
)


@pytest.fixture(scope="module")
def translator():
    """Crée un traducteur léger (Opus-MT FR→EN)."""
    config = TranslationConfig(
        model_name="Helsinki-NLP/opus-mt-fr-en",
        device="cpu",
        num_beams=1,
    )
    try:
        return TranslatorProcessor(config)
    except Exception as e:
        pytest.skip(f"Modèle indisponible: {e}")


def test_lang_codes_present():
    assert "fr" in TranslatorProcessor.NLLB_LANG_CODES
    assert "en" in TranslatorProcessor.NLLB_LANG_CODES
    assert TranslatorProcessor.NLLB_LANG_CODES["fr"] == "fra_Latn"


def test_empty_string(translator):
    assert translator.translate("", "fr", "en") == ""


def test_whitespace_only(translator):
    assert translator.translate("   ", "fr", "en") == ""


@pytest.mark.slow
def test_translation_fr_to_en(translator):
    result = translator.translate("Bonjour", "fr", "en")
    assert isinstance(result, str)
    assert len(result) > 0
    assert result.lower().startswith(("hello", "hi", "good"))


@pytest.mark.slow
def test_translation_simple_sentence(translator):
    result = translator.translate("Je voudrais un café.", "fr", "en")
    assert len(result) > 0
    assert "coffee" in result.lower() or "café" in result.lower()
