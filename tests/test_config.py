import pytest
from src.config import normalize_language_code, validate_language_code
from src.translations import load_translations

# Load translations for the test
load_translations('en')

@pytest.mark.parametrize("input_lang, expected_lang", [
    ("en", "en"),
    ("en-us", "en-US"),
    ("en-GB", "en-GB"),
    ("pt", "pt-BR"),
    ("pt-br", "pt-BR"),
    ("es", "es-US"),
    ("fr", "fr-FR"),
    ("de", "de-DE"),
    ("zh-cn", "zh-CN"),
    ("unmapped-lang", "unmapped-lang"),
])
def test_normalize_language_code(input_lang, expected_lang):
    """Tests that language codes are correctly normalized."""
    assert normalize_language_code(input_lang) == expected_lang

@pytest.mark.parametrize("lang, expected", [
    ("en", True),
    ("en-us", True),
    ("fr-fr", True),
    ("zz", False),
    ("123", False),
])
def test_validate_language_code(lang, expected):
    """Tests the language code validation."""
    assert validate_language_code(lang) == expected