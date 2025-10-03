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
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secrets.json"
CONFIG_FILE = "config.json"

# --- Regional Language Mapping ---
REGIONAL_LANGUAGE_MAP = {
    'ar': 'ar', 'bn': 'bn', 'nl': 'nl-NL', 'fr': 'fr-FR', 'de': 'de-DE',
    'hi': 'hi', 'id': 'id', 'it': 'it', 'ja': 'ja', 'ko': 'ko', 'ml': 'ml',
    'pl': 'pl', 'pt': 'pt-BR', 'pt-br': 'pt-BR', 'pa': 'pa', 'ru': 'ru',
    'es': 'es-US', 'es-us': 'es-US', 'ta': 'ta', 'te': 'te', 'uk': 'uk',
    'en': 'en', 'en-us': 'en-US', 'en-gb': 'en-GB', 'zh': 'zh', 'zh-cn': 'zh-CN',
    'zh-tw': 'zh-TW', 'zh-hk': 'zh-HK',
}

def normalize_language_code(lang):
    """Normalizes language codes to match YouTube's regional requirements."""
    lang_lower = lang.lower().strip()
    if lang_lower in REGIONAL_LANGUAGE_MAP:
        normalized = REGIONAL_LANGUAGE_MAP[lang_lower]
        if normalized != lang:
            print(f"{T.INFO}    {E.INFO} Language code '{lang}' normalized to '{normalized}' for YouTube compatibility.")
        return normalized
    return lang

def validate_language_code(lang):
    """Validate if language code is supported by YouTube for subtitles"""
    valid_codes = [
        'aa', 'ab', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch',
        'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'de-de', 'dv', 'dz', 'ee', 'el', 'en', 'en-us', 'en-gb', 'eo', 'es', 'es-us', 'et', 'eu', 'fa',
        'ff', 'fi', 'fj', 'fo', 'fr', 'fr-fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia',
        'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku',
        'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my',
        'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nl-nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt',
        'pt-br', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss',
        'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've',
        'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zh-cn', 'zh-tw', 'zh-hk', 'zu'
    ]
    return lang.lower() in valid_codes

def validate_config(config):
    """Validates the structure of the configuration dictionary."""
    if "channels" not in config or not isinstance(config["channels"], dict) or not config["channels"]:
        raise ValueError("Config file must have a non-empty 'channels' dictionary.")
    for nickname, channel_id in config["channels"].items():
        if not isinstance(channel_id, str) or not channel_id.startswith("UC"):
            raise ValueError(f"Invalid channel ID for nickname '{nickname}'. It must be a string starting with 'UC'.")

def load_config():
    """Loads and validates the configuration file."""
    if not os.path.exists(CONFIG_FILE):
        print(f"{T.FAIL}{E.FAIL} Configuration file '{CONFIG_FILE}' not found. Please create it.")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        validate_config(config)
        return config
    except (json.JSONDecodeError, ValueError) as e:
        print(f"{T.FAIL}{E.FAIL} Configuration error: {e}")
        sys.exit(1)