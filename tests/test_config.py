import pytest
from src.config import normalize_language_code

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