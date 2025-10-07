import pytest
from unittest.mock import patch, MagicMock
from src.quota import increment_quota, get_total_quota_usage, display_quota_usage, QUOTA_COSTS

@pytest.fixture
def mock_translator():
    """Fixture to mock the Translator class."""
    translator = MagicMock()
    translator.get.side_effect = lambda key, **kwargs: key
    return translator

@pytest.fixture(autouse=True)
def reset_quota_usage():
    """Reset the quota usage counter before each test."""
    from src import quota
    quota._QUOTA_USAGE = 0
    yield

def test_increment_quota(mock_translator):
    """Test that increment_quota correctly adds to the total usage."""
    with patch('builtins.print'): # Suppress print output
        increment_quota('captions.insert', mock_translator)
        assert get_total_quota_usage() == QUOTA_COSTS['captions.insert']

        increment_quota('channels.list', mock_translator)
        expected_total = QUOTA_COSTS['captions.insert'] + QUOTA_COSTS['channels.list']
        assert get_total_quota_usage() == expected_total

def test_increment_quota_unknown_call(mock_translator):
    """Test that an unknown API call does not increment the quota."""
    with patch('builtins.print'):
        initial_usage = get_total_quota_usage()
        increment_quota('unknown.api.call', mock_translator)
        assert get_total_quota_usage() == initial_usage

@patch('builtins.print')
def test_display_quota_usage(mock_print, mock_translator):
    """Test that the quota usage is displayed correctly."""
    # Arrange
    with patch('builtins.print'): # Suppress increment_quota prints
        increment_quota('captions.list', mock_translator)
        increment_quota('captions.list', mock_translator)

    total_usage = get_total_quota_usage()

    # Act
    display_quota_usage(mock_translator)

    # Assert
    # Check that the translator was called with the correct key and arguments
    mock_translator.get.assert_any_call('quota.report_total', total_usage=total_usage)