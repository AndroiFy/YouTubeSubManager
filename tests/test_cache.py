import os
import time
import json
import pytest
from datetime import timedelta
from src.cache import (
    generate_cache_key,
    get_from_cache,
    save_to_cache,
    _get_cache_path,
    CACHE_DURATION
)

@pytest.fixture(autouse=True)
def setup_teardown(tmp_path):
    """Ensure each test runs in a clean temporary directory."""
    original_cwd = os.getcwd()
    # Ugly hack to make the cache module use the temp dir
    from src import cache
    cache.CACHE_DIR = tmp_path
    yield
    os.chdir(original_cwd)

def test_generate_cache_key_is_deterministic():
    """Test that the cache key generation is deterministic."""
    key1 = generate_cache_key("my_func", param1="a", param2="b")
    key2 = generate_cache_key("my_func", param2="b", param1="a") # Order should not matter
    key3 = generate_cache_key("my_func", param1="a", param2="c")
    assert key1 == key2
    assert key1 != key3

def test_save_and_get_from_cache(tmp_path):
    """Test saving to and retrieving from the cache."""
    key = "test_key"
    data = {"message": "hello world"}

    save_to_cache(key, data)

    # Verify file was created
    cache_file = _get_cache_path(key)
    assert os.path.exists(cache_file)

    # Verify content
    retrieved_data = get_from_cache(key)
    assert retrieved_data == data

def test_cache_expiration(tmp_path):
    """Test that the cache expires after the specified duration."""
    key = "expiring_key"
    data = {"message": "this will expire"}

    # Temporarily set a very short cache duration for the test
    from src import cache
    original_duration = cache.CACHE_DURATION
    cache.CACHE_DURATION = timedelta(seconds=1)

    save_to_cache(key, data)

    # Should be valid initially
    assert get_from_cache(key) == data

    # Wait for it to expire
    time.sleep(1.5)

    assert get_from_cache(key) is None

    # Restore original duration
    cache.CACHE_DURATION = original_duration

def test_get_from_invalid_cache_file(tmp_path):
    """Test that an invalid or corrupted cache file is handled correctly."""
    key = "invalid_key"
    cache_file = _get_cache_path(key)

    # Create a corrupted JSON file
    with open(cache_file, 'w') as f:
        f.write("{'invalid_json':}")

    assert get_from_cache(key) is None