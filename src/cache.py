import os
import json
import hashlib
from datetime import datetime, timedelta

CACHE_DIR = "cache"
CACHE_DURATION = timedelta(hours=1)

def _get_cache_path(key):
    """Constructs the full path for a given cache key."""
    return os.path.join(CACHE_DIR, f"{key}.json")

def generate_cache_key(function_name, **kwargs):
    """Generates a unique, stable cache key from a function name and its arguments."""
    # Create a stable string representation of the arguments
    sorted_kwargs = sorted(kwargs.items())
    args_str = json.dumps(sorted_kwargs)

    # Hash the combination of function name and arguments
    hasher = hashlib.md5()
    hasher.update(function_name.encode('utf-8'))
    hasher.update(args_str.encode('utf-8'))

    return hasher.hexdigest()

def get_from_cache(key):
    """
    Retrieves data from the cache if it exists and is not expired.
    Returns None if the cache is invalid or missing.
    """
    cache_path = _get_cache_path(key)
    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Check if cache is expired
        cached_time = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cached_time > CACHE_DURATION:
            return None

        return cache_data['data']
    except (json.JSONDecodeError, KeyError, IOError):
        # Invalid cache file, treat as a cache miss
        return None

def save_to_cache(key, data):
    """Saves data to the cache with a timestamp."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = _get_cache_path(key)

    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'data': data
    }

    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4)
    except IOError as e:
        print(f"Warning: Could not write to cache file {cache_path}: {e}")