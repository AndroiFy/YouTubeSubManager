import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open, ANY
from src.file_handler import sync_project
from datetime import datetime, timezone

@pytest.fixture
def mock_youtube_api():
    """Fixture to mock the YouTube API client."""
    return MagicMock()

@pytest.fixture
def mock_translator():
    """Fixture to mock the Translator class."""
    translator = MagicMock()
    translator.get.side_effect = lambda key, **kwargs: key
    return translator

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('os.path.exists')
@patch('os.walk')
@patch('builtins.open', new_callable=mock_open)
def test_sync_new_structure_new_file_upload(mock_open_file, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api, mock_translator):
    """
    Test that a new local file in the new folder structure is correctly uploaded.
    """
    # Arrange
    project_name = "sync_test"
    project_path = f"projects/{project_name}"
    video_folder_path = os.path.join(project_path, 'video1')

    initial_project_data = {"video1": {"title": "Test Video 1", "subtitles": {}}}
    mock_open_file.return_value.read.return_value = json.dumps(initial_project_data)

    mock_walk.return_value = [
        (project_path, ['video1'], []),
        (video_folder_path, [], ['en.srt'])
    ]
    mock_exists.return_value = True

    mock_upload.return_value = {
        'id': 'new_caption_id',
        'snippet': {'lastUpdated': datetime.now(timezone.utc).isoformat()}
    }

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel", mock_translator)

    # Assert
    mock_upload.assert_called_once_with(mock_youtube_api, 'video1', 'en', ANY, mock_translator)
    mock_update.assert_not_called()
    mock_delete.assert_not_called()

    written_content = "".join(c.args[0] for c in mock_open_file().write.call_args_list)
    final_project_data = json.loads(written_content)

    assert final_project_data['video1']['subtitles']['en']['status'] == 'synced'
    assert final_project_data['video1']['subtitles']['en']['caption_id'] == 'new_caption_id'

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('os.path.exists')
@patch('os.walk')
@patch('os.path.getmtime')
@patch('builtins.open', new_callable=mock_open)
def test_sync_new_structure_modified_file_update(mock_open_file, mock_getmtime, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api, mock_translator):
    """
    Test that a modified local file in the new folder structure is correctly updated.
    """
    # Arrange
    project_name = "sync_test_update"
    project_path = f"projects/{project_name}"
    video_folder_path = os.path.join(project_path, 'video1')

    initial_project_data = {
        "video1": {
            "title": "Test Video 1",
            "subtitles": {
                "en": {
                    "caption_id": "caption1_en",
                    "last_sync": datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat(),
                    "local_path": os.path.join(video_folder_path, "en.srt")
                }
            }
        }
    }
    mock_open_file.return_value.read.return_value = json.dumps(initial_project_data)

    mock_walk.return_value = [(project_path, ['video1'], []), (video_folder_path, [], ['en.srt'])]
    mock_exists.return_value = True
    mock_getmtime.return_value = datetime(2023, 1, 2, 0, 0, 0).timestamp()

    mock_update.return_value = {
        'id': 'caption1_en',
        'snippet': {'lastUpdated': datetime.now(timezone.utc).isoformat()}
    }

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel", mock_translator)

    # Assert
    mock_update.assert_called_once_with(mock_youtube_api, 'video1', 'en', ANY, mock_translator, caption_id='caption1_en')
    mock_upload.assert_not_called()
    mock_delete.assert_not_called()

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('os.path.exists')
@patch('os.walk')
@patch('builtins.open', new_callable=mock_open)
def test_sync_flat_structure_backward_compatibility(mock_open_file, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api, mock_translator):
    """
    Test that a new local file in the old flat structure is correctly uploaded for backward compatibility.
    """
    # Arrange
    project_name = "sync_test"
    project_path = f"projects/{project_name}"

    initial_project_data = {"video1": {"title": "Test Video 1", "subtitles": {}}}
    mock_open_file.return_value.read.return_value = json.dumps(initial_project_data)

    mock_walk.return_value = [(project_path, [], ['video1_en.srt'])]
    mock_exists.return_value = True

    mock_upload.return_value = {
        'id': 'new_caption_id',
        'snippet': {'lastUpdated': datetime.now(timezone.utc).isoformat()}
    }

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel", mock_translator)

    # Assert
    mock_upload.assert_called_once_with(mock_youtube_api, 'video1', 'en', ANY, mock_translator)

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('os.path.exists')
@patch('os.walk')
@patch('builtins.open', new_callable=mock_open)
def test_sync_project_deleted_file(mock_open_file, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api, mock_translator):
    """
    Test that a deleted local file results in the remote caption being deleted.
    """
    # Arrange
    project_name = "sync_test_delete"
    project_path = f"projects/{project_name}"

    initial_project_data = {
        "video1": {
            "title": "Test Video 1",
            "subtitles": {
                "en": {
                    "caption_id": "caption_to_delete",
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
            }
        }
    }
    mock_open_file.return_value.read.return_value = json.dumps(initial_project_data)

    mock_walk.return_value = [(project_path, [], [])]
    mock_exists.return_value = True

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel", mock_translator)

    # Assert
    mock_delete.assert_called_once_with(mock_youtube_api, "caption_to_delete", mock_translator)
    mock_upload.assert_not_called()
    mock_update.assert_not_called()

    written_content = "".join(c.args[0] for c in mock_open_file().write.call_args_list)
    final_project_data = json.loads(written_content)

    assert 'en' not in final_project_data['video1']['subtitles']