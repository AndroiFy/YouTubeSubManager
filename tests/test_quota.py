import pytest
from unittest.mock import patch
from src.quota import increment_quota, get_total_quota_usage, display_quota_usage, QUOTA_COSTS

@pytest.fixture(autouse=True)
def reset_quota_usage():
    """Reset the quota usage counter before each test."""
    from src import quota
    quota._QUOTA_USAGE = 0
    yield

def test_increment_quota():
    """Test that increment_quota correctly adds to the total usage."""
    with patch('builtins.print'): # Suppress print output
        increment_quota('captions.insert')
        assert get_total_quota_usage() == QUOTA_COSTS['captions.insert']

        increment_quota('channels.list')
        expected_total = QUOTA_COSTS['captions.insert'] + QUOTA_COSTS['channels.list']
        assert get_total_quota_usage() == expected_total

def test_increment_quota_unknown_call():
    """Test that an unknown API call does not increment the quota."""
    with patch('builtins.print'):
        initial_usage = get_total_quota_usage()
        increment_quota('unknown.api.call')
        assert get_total_quota_usage() == initial_usage

@patch('builtins.print')
def test_display_quota_usage(mock_print):
    """Test that the quota usage is displayed correctly."""
    # Arrange
    with patch('builtins.print'): # Suppress increment_quota prints
        increment_quota('captions.list')
        increment_quota('captions.list')

    total_usage = get_total_quota_usage()

    # Act
    display_quota_usage()

    # Assert
    # Check that the print output contains the total usage
    # The line with the total usage is the third from the end.
    usage_line_args = mock_print.call_args_list[-3][0]
    assert str(total_usage) in usage_line_args[0]