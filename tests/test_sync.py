import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from src.file_handler import sync_project
from datetime import datetime, timezone

@pytest.fixture
def mock_youtube_api():
    """Fixture to mock the YouTube API client."""
    return MagicMock()

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('os.path.exists')
@patch('os.walk')
@patch('builtins.open', new_callable=mock_open)
def test_sync_project_new_file_upload(mock_open_file, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api):
    """
    Test that a new local file is correctly identified and uploaded.
    """
    # Arrange
    project_name = "sync_test"
    project_path = f"projects/{project_name}"
    subtitles_json_path = f"{project_path}/subtitles.json"

    # Mock project file data
    initial_project_data = {
        "video1": {
            "title": "Test Video 1",
            "subtitles": {}
        }
    }
    mock_open_file.return_value.read.return_value = json.dumps(initial_project_data)

    # Mock os.walk to find a new local file
    new_file_path = f"{project_path}/video1_en.srt"
    mock_walk.return_value = [
        (project_path, [], ['video1_en.srt']),
    ]
    mock_exists.return_value = True # For the subtitles.json file

    # Mock the upload response
    mock_upload.return_value = {
        'id': 'new_caption_id',
        'snippet': {
            'lastUpdated': datetime.now(timezone.utc).isoformat()
        }
    }

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel")

    # Assert
    mock_upload.assert_called_once()
    call_args = mock_upload.call_args[0]
    assert call_args[1] == 'video1' # video_id
    assert call_args[2] == 'en'     # language

    mock_update.assert_not_called()
    mock_delete.assert_not_called()

    # Verify that the project file was updated
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
def test_sync_project_modified_file_update(mock_open_file, mock_getmtime, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api):
    """
    Test that a modified local file is correctly identified and updated.
    """
    # Arrange
    project_name = "sync_test_update"
    project_path = f"projects/{project_name}"

    # Mock project file with an already synced file
    initial_project_data = {
        "video1": {
            "title": "Test Video 1",
            "subtitles": {
                "en": {
                    "caption_id": "caption1_en",
                    "last_sync": datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat(),
                    "local_path": f"{project_path}/video1_en.srt"
                }
            }
        }
    }
    mock_open_file.return_value.read.return_value = json.dumps(initial_project_data)

    # Mock os.walk to find the same file
    mock_walk.return_value = [
        (project_path, [], ['video1_en.srt']),
    ]
    mock_exists.return_value = True

    # Mock the modification time to be newer than the last sync
    mock_getmtime.return_value = datetime(2023, 1, 2, 0, 0, 0).timestamp()

    # Mock the update response
    mock_update.return_value = {
        'id': 'caption1_en',
        'snippet': {
            'lastUpdated': datetime.now(timezone.utc).isoformat()
        }
    }

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel")

    # Assert
    mock_update.assert_called_once()
    mock_upload.assert_not_called()
    mock_delete.assert_not_called()

    # Verify that the project file was updated
    written_content = "".join(c.args[0] for c in mock_open_file().write.call_args_list)
    final_project_data = json.loads(written_content)

    assert final_project_data['video1']['subtitles']['en']['status'] == 'synced'
    # Check that the last_sync time has been updated
    assert datetime.fromisoformat(final_project_data['video1']['subtitles']['en']['last_sync']) > datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('os.path.exists')
@patch('os.walk')
@patch('builtins.open', new_callable=mock_open)
def test_sync_project_deleted_file(mock_open_file, mock_walk, mock_exists, mock_delete, mock_update, mock_upload, mock_youtube_api):
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

    # Mock os.walk to return no files, simulating a deletion
    mock_walk.return_value = [
        (project_path, [], []),
    ]
    mock_exists.return_value = True

    # Act
    sync_project(mock_youtube_api, project_name, "test_channel")

    # Assert
    mock_delete.assert_called_once_with(mock_youtube_api, "caption_to_delete")
    mock_upload.assert_not_called()
    mock_update.assert_not_called()

    # Verify that the subtitle was removed from the project file
    written_content = "".join(c.args[0] for c in mock_open_file().write.call_args_list)
    final_project_data = json.loads(written_content)

    assert 'en' not in final_project_data['video1']['subtitles']