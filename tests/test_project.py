import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from src.file_handler import create_project

@pytest.fixture
def mock_youtube_api():
    """Fixture to mock the YouTube API client."""
    return MagicMock()

@patch('src.file_handler.get_channel_videos')
@patch('src.file_handler.list_captions')
@patch('os.makedirs')
@patch('os.path.exists', return_value=False)
def test_create_project_success(mock_exists, mock_makedirs, mock_list_captions, mock_get_channel_videos, mock_youtube_api):
    """
    Test the successful creation of a new project.
    """
    # Arrange
    project_name = "my_new_project"
    channel_id = "UC1234567890"

    mock_get_channel_videos.return_value = [
        {'id': 'video1', 'title': 'Test Video 1'},
        {'id': 'video2', 'title': 'Test Video 2'}
    ]

    mock_list_captions.side_effect = [
        {
            'items': [
                {'id': 'caption1_en', 'snippet': {'language': 'en', 'lastUpdated': '2023-01-01T00:00:00Z', 'isDraft': False}},
                {'id': 'caption1_fr', 'snippet': {'language': 'fr', 'lastUpdated': '2023-01-02T00:00:00Z', 'isDraft': False}}
            ]
        },
        {
            'items': []
        }
    ]

    # Act
    with patch('builtins.open', mock_open()) as mock_file:
        create_project(mock_youtube_api, channel_id, project_name)

    # Assert
    project_path = os.path.join("projects", project_name)
    subtitles_json_path = os.path.join(project_path, "subtitles.json")

    mock_makedirs.assert_called_once_with(project_path, exist_ok=True)
    mock_file.assert_called_once_with(subtitles_json_path, 'w', encoding='utf-8')

    written_content = "".join(c.args[0] for c in mock_file().write.call_args_list)
    written_data = json.loads(written_content)

    assert 'video1' in written_data
    assert 'video2' in written_data
    assert written_data['video1']['title'] == 'Test Video 1'
    assert 'en' in written_data['video1']['subtitles']
    assert written_data['video1']['subtitles']['en']['caption_id'] == 'caption1_en'
    assert len(written_data['video2']['subtitles']) == 0