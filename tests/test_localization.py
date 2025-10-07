import pytest
import json
from unittest.mock import patch, mock_open
from src.localization import Translator

@pytest.fixture
def mock_en_locale():
    """Fixture to mock the English locale file."""
    locale_data = {
        "greeting": "Hello, {name}!",
        "messages": {
            "welcome": "Welcome to the application."
        }
    }
    return json.dumps(locale_data)

def test_translator_loads_language_successfully(mock_en_locale):
    """Test that the Translator correctly loads a valid language file."""
    with patch('builtins.open', mock_open(read_data=mock_en_locale)):
        with patch('os.path.exists', return_value=True):
            translator = Translator(language='en')
            assert translator.translations is not None
            assert translator.translations["greeting"] == "Hello, {name}!"

def test_translator_get_retrieves_key(mock_en_locale):
    """Test that the get() method retrieves and formats a key."""
    with patch('builtins.open', mock_open(read_data=mock_en_locale)):
        with patch('os.path.exists', return_value=True):
            translator = Translator(language='en')

            # Test simple key
            welcome_msg = translator.get('messages.welcome')
            assert welcome_msg == "Welcome to the application."

            # Test key with formatting
            greeting_msg = translator.get('greeting', name="Jules")
            assert greeting_msg == "Hello, Jules!"

def test_translator_fallback_for_missing_key(mock_en_locale):
    """Test that the get() method falls back to the key if not found."""
    with patch('builtins.open', mock_open(read_data=mock_en_locale)):
        with patch('os.path.exists', return_value=True):
            translator = Translator(language='en')

            # Test a key that doesn't exist
            missing_msg = translator.get('nonexistent.key')
            assert missing_msg == 'nonexistent.key'

def test_translator_fallback_to_english(mock_en_locale):
    """Test that the Translator falls back to English if a language file is not found."""
    # Mock os.path.exists to return False for 'es.json' but True for 'en.json'
    def mock_exists(path):
        if path.endswith('es.json'):
            return False
        return True

    with patch('os.path.exists', side_effect=mock_exists):
        with patch('builtins.open', mock_open(read_data=mock_en_locale)):
            translator = Translator(language='es')
            # Should have fallen back to English
            assert translator.language == 'en'
            assert translator.get('messages.welcome') == "Welcome to the application."

def test_translator_handles_missing_english_fallback():
    """Test that the Translator handles when even the English fallback is missing."""
    with patch('os.path.exists', return_value=False):
        translator = Translator(language='es')
        assert translator.language == 'en'
        assert translator.translations == {}
        assert translator.get('any.key') == 'any.key'

def test_translator_handles_invalid_json():
    """Test that the Translator handles a corrupted JSON file."""
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data="{invalid_json}")):
            translator = Translator(language='en')
            assert translator.translations == {}
            assert translator.get('any.key') == 'any.key'