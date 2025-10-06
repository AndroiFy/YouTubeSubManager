import os
import json
import pytest
from src.config import load_config

@pytest.fixture(scope="function")
def temp_config_file(tmp_path):
    config_data = {
        "channels": {
            "test_channel": "UC1234567890"
        }
    }
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield
    os.chdir(original_cwd)

def test_load_config_success(temp_config_file):
    """
    Test that load_config returns the correct configuration data when the file is valid.
    """
    config = load_config()
    assert "channels" in config
    assert "test_channel" in config["channels"]
    assert config["channels"]["test_channel"] == "UC1234567890"

def test_load_config_not_found(tmp_path):
    """
    Test that load_config exits when the config file is not found.
    """
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        load_config()
    assert e.type == SystemExit
    assert e.value.code == 1
    os.chdir(original_cwd)

def test_load_config_invalid_json(tmp_path):
    """
    Test that load_config exits with invalid JSON.
    """
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        f.write("{'invalid_json':}")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        load_config()
    assert e.type == SystemExit
    assert e.value.code == 1
    os.chdir(original_cwd)

def test_validate_config_no_channels_key(tmp_path):
    """
    Test that load_config exits if 'channels' key is missing.
    """
    config_data = {"other_key": "value"}
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        load_config()
    assert e.type == SystemExit
    assert e.value.code == 1
    os.chdir(original_cwd)