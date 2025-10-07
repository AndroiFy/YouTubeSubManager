import os
import sys
import json
from colorama import init, Fore, Style

init(autoreset=True)

# --- Style Definitions ---
class T:
    HEADER, OK, INFO, WARN, FAIL = Fore.MAGENTA + Style.BRIGHT, Fore.GREEN + Style.BRIGHT, Fore.CYAN, Fore.YELLOW, Fore.RED + Style.BRIGHT

class E:
    SUCCESS, INFO, WARN, FAIL, KEY, ROCKET, CHANNEL, FILE, DOWNLOAD, PROCESS, VIDEO, TRASH, REPORT = "✅", "ℹ️", "⚠️", "❌", "🔑", "🚀", "📺", "📄", "📥", "⚙️", "🎞️", "🗑️", "📊"

# --- Configuration ---
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME, API_VERSION, CLIENT_SECRETS_FILE, CONFIG_FILE = "youtube", "v3", "client_secrets.json", "config.json"

# --- Regional Language Mapping ---
REGIONAL_LANGUAGE_MAP = {
    'ar': 'ar', 'bn': 'bn', 'nl': 'nl-NL', 'fr': 'fr-FR', 'de': 'de-DE',
    'hi': 'hi', 'id': 'id', 'it': 'it', 'ja': 'ja', 'ko': 'ko', 'ml': 'ml',
    'pl': 'pl', 'pt': 'pt-BR', 'pt-br': 'pt-BR', 'pa': 'pa', 'ru': 'ru',
    'es': 'es-US', 'es-us': 'es-US', 'ta': 'ta', 'te': 'te', 'uk': 'uk',
    'en': 'en', 'en-us': 'en-US', 'en-gb': 'en-GB', 'zh': 'zh', 'zh-cn': 'zh-CN',
    'zh-tw': 'zh-TW', 'zh-hk': 'zh-HK',
}

def normalize_language_code(lang, translator):
    """
    Normalizes language codes to match YouTube's regional requirements.
    Returns the appropriate regional variant if available.
    """
    lang_lower = lang.lower().strip()

    if lang_lower in REGIONAL_LANGUAGE_MAP:
        normalized = REGIONAL_LANGUAGE_MAP[lang_lower]
        if normalized != lang:
            print(translator.get('config.lang_normalized', T_INFO=T.INFO, E_INFO=E.INFO, lang=lang, normalized=normalized))
        return normalized

    return lang

def validate_config(config, translator):
    """Validates the structure of the configuration dictionary."""
    if not isinstance(config, dict):
        raise ValueError(translator.get('config.must_be_dict'))
    if "channels" not in config:
        raise ValueError(translator.get('config.must_have_channels'))
    if not isinstance(config["channels"], dict):
        raise ValueError(translator.get('config.channels_must_be_dict'))
    if not config["channels"]:
        raise ValueError(translator.get('config.channels_not_empty'))
    for nickname, channel_id in config["channels"].items():
        if not isinstance(channel_id, str) or not channel_id.startswith("UC"):
            raise ValueError(translator.get('config.invalid_channel_id', nickname=nickname))

def load_config(translator):
    if not os.path.exists(CONFIG_FILE):
        print(translator.get('config.file_not_found', T_FAIL=T.FAIL, E_FAIL=E.FAIL, config_file=CONFIG_FILE))
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        validate_config(config, translator)
        return config
    except json.JSONDecodeError as e:
        print(translator.get('config.invalid_json', T_FAIL=T.FAIL, E_FAIL=E.FAIL, e=e))
        sys.exit(1)
    except ValueError as e:
        print(translator.get('config.config_error', T_FAIL=T.FAIL, E_FAIL=E.FAIL, e=e))
        sys.exit(1)

def validate_language_code(lang):
    """Validate if language code is supported by YouTube for subtitles"""
    valid_codes = [
        'aa', 'ab', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az',
        'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs',
        'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy',
        'da', 'de', 'de-de', 'dv', 'dz',
        'ee', 'el', 'en', 'en-us', 'en-gb', 'eo', 'es', 'es-us', 'et', 'eu',
        'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fr-fr', 'fy',
        'ga', 'gd', 'gl', 'gn', 'gu', 'gv',
        'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz',
        'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu',
        'ja', 'jv',
        'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky',
        'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv',
        'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my',
        'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nl-nl', 'nn', 'no', 'nr', 'nv', 'ny',
        'oc', 'oj', 'om', 'or', 'os',
        'pa', 'pi', 'pl', 'ps', 'pt', 'pt-br',
        'qu',
        'rm', 'rn', 'ro', 'ru', 'rw',
        'sa', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw',
        'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty',
        'ug', 'uk', 'ur', 'uz',
        've', 'vi', 'vo',
        'wa', 'wo',
        'xh',
        'yi', 'yo',
        'za', 'zh', 'zh-cn', 'zh-tw', 'zh-hk', 'zu'
    ]
    return lang.lower() in valid_codes