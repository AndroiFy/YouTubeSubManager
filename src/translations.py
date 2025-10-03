import json
import os

TRANSLATIONS = {}
DEFAULT_LANG = "en"

def load_translations(lang):
    """Loads the translation file for the given language."""
    global TRANSLATIONS

    # Fallback to English if the selected language is not available
    if not os.path.exists(f"locales/{lang}.json"):
        print(f"Warning: Language '{lang}' not found. Falling back to English.")
        lang = DEFAULT_LANG

    try:
        with open(f"locales/{lang}.json", 'r', encoding='utf-8') as f:
            TRANSLATIONS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading translation file for '{lang}': {e}")
        # Load English as a last resort
        if lang != DEFAULT_LANG:
            load_translations(DEFAULT_LANG)
        else:
            # If English fails to load, something is seriously wrong
            print("FATAL: Could not load the default English translation file.")
            exit(1)

def get_string(key, **kwargs):
    """Gets a translated string by its key and formats it with any provided arguments."""
    return TRANSLATIONS.get(key, key).format(**kwargs)