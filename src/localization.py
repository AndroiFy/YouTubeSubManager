import os
import json
from src.config import T, E

class Translator:
    def __init__(self, language='en'):
        self.language = language
        self.translations = self._load_translations()

    def _load_translations(self):
        """Loads the translation file for the selected language."""
        locale_path = os.path.join("locales", f"{self.language}.json")
        if not os.path.exists(locale_path):
            print(f"{T.WARN}{E.WARN} Language file not found for '{self.language}'. Falling back to 'en'.")
            self.language = 'en'
            locale_path = os.path.join("locales", "en.json")
            if not os.path.exists(locale_path):
                # If even English is missing, return an empty dict
                return {}

        try:
            with open(locale_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"{T.FAIL}{E.FAIL} Failed to load language file {locale_path}: {e}")
            return {}

    def get(self, key, **kwargs):
        """
        Retrieves a translated string by its key and formats it with provided arguments.
        Falls back to the key itself if the translation is not found.
        """
        # Navigate nested keys if necessary
        keys = key.split('.')
        value = self.translations
        try:
            for k in keys:
                value = value[k]

            # Perform formatting if arguments are provided
            return value.format(**kwargs)
        except KeyError:
            # Fallback to the key itself if not found
            return key
        except Exception as e:
            print(f"{T.WARN}    {E.WARN} Translation formatting error for key '{key}': {e}")
            return key # Return the key as a fallback