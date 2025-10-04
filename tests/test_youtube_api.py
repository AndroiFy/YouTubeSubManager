import pytest
from unittest.mock import Mock, patch
from src.youtube_api import upload_caption, update_caption, delete_caption
from src.translations import load_translations

# Load translations for the test
load_translations('en')

@patch('src.youtube_api.MediaFileUpload')
def test_upload_caption(mock_media_file_upload):
    """Tests that upload_caption calls the API correctly."""
    mock_youtube = Mock()
    mock_youtube.captions.return_value.insert.return_value.execute.return_value = {'id': 'new_caption_id'}

    upload_caption(mock_youtube, "video_id", "en", "/tmp/file.srt")

    mock_youtube.captions.return_value.insert.assert_called_once_with(
        part="snippet",
        body={'snippet': {'videoId': 'video_id', 'language': 'en', 'isDraft': False}},
        media_body=mock_media_file_upload.return_value
    )

@patch('src.youtube_api.MediaFileUpload')
def test_update_caption(mock_media_file_upload):
    """Tests that update_caption calls the API correctly."""
    mock_youtube = Mock()

    update_caption(mock_youtube, "video_id", "en", "/tmp/file.srt", caption_id="existing_id")

    mock_youtube.captions.return_value.update.assert_called_once()

def test_delete_caption():
    """Tests that delete_caption calls the API correctly."""
    mock_youtube = Mock()

    delete_caption(mock_youtube, "caption_id")

    mock_youtube.captions.return_value.delete.assert_called_once_with(id="caption_id")