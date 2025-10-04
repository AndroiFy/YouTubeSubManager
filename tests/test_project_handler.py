import pytest
import os
import json
from unittest.mock import Mock, patch, mock_open
from src.project_handler import create_project, sync_project
from src.translations import load_translations

# Load translations for the test
load_translations('en')

@patch('src.project_handler.os.makedirs')
@patch('src.project_handler.open', new_callable=mock_open)
@patch('src.project_handler.json.dump')
def test_create_project_success(mock_json_dump, mock_file, mock_makedirs):
    """Tests the successful creation of a project."""
    mock_youtube = Mock()
    mock_youtube.videos.return_value.list.return_value.execute.return_value = {
        'items': [{'snippet': {'title': 'Test Video'}}]
    }
    mock_youtube.captions.return_value.list.return_value.execute.return_value = {
        'items': [{'id': 'cap1', 'snippet': {'language': 'en'}}]
    }
    mock_youtube.captions.return_value.download.return_value.execute.return_value = "subtitle_body"

    create_project(mock_youtube, "video_id_123")

    mock_makedirs.assert_called_once_with(os.path.join("projects", "video_id_123_Test Video", "subtitles"), exist_ok=True)
    mock_youtube.captions.return_value.download.assert_called_once_with(id='cap1', tfmt='srt')

    # Check that status.json is written correctly
    mock_json_dump.assert_called_once()
    args, kwargs = mock_json_dump.call_args
    status_data = args[0]
    assert status_data['video_id'] == 'video_id_123'
    assert len(status_data['captions']) == 1
    assert status_data['captions'][0]['language'] == 'en'

@patch('src.project_handler.os.listdir')
@patch('src.project_handler.os.path.exists')
@patch('src.project_handler.open', new_callable=mock_open)
@patch('src.project_handler.json.load')
@patch('src.project_handler.upload_caption')
@patch('src.project_handler.update_caption')
@patch('src.project_handler.delete_caption')
@patch('src.utils.confirm_quota', return_value=True)
def test_sync_project_all_actions(mock_confirm, mock_delete, mock_update, mock_upload, mock_json_load, mock_file_open, mock_path_exists, mock_listdir):
    """Tests the sync command with uploads, updates, and deletes."""
    mock_youtube = Mock()
    mock_path_exists.return_value = True

    # Remote state
    mock_json_load.return_value = {
        "video_id": "vid1",
        "captions": [
            {"language": "en", "caption_id": "cap_en"},
            {"language": "es", "caption_id": "cap_es"} # This one will be deleted
        ]
    }

    # Local state
    mock_listdir.return_value = ["en.srt", "fr.srt"] # fr is new, es is missing

    # Mock the final status update call
    mock_youtube.captions.return_value.list.return_value.execute.return_value = {'items': []}

    sync_project(mock_youtube, "project_path", allow_deletes=True, dry_run=False)

    # Check that upload is called for the new file (fr)
    mock_upload.assert_called_once()
    # Check that update is called for the existing file (en)
    mock_update.assert_called_once()
    # Check that delete is called for the missing file (es)
    mock_delete.assert_called_once()