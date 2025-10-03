import pytest
from unittest.mock import Mock, patch
from src.youtube_api import upload_caption, delete_caption

@patch('src.youtube_api.MediaFileUpload')
def test_upload_caption_dry_run(mock_media_file_upload):
    """Tests that upload_caption in dry run mode does not call the API."""
    mock_youtube = Mock()
    upload_caption(mock_youtube, "video_id", "en", "/tmp/file.srt", dry_run=True)
    mock_youtube.captions().insert.assert_not_called()

@patch('src.youtube_api.MediaFileUpload')
def test_upload_caption_live_run(mock_media_file_upload):
    """Tests that upload_caption in live mode calls the API."""
    mock_youtube = Mock()
    # Configure the mock chain without calling the methods
    mock_youtube.captions.return_value.insert.return_value.execute.return_value = {'id': 'new_caption_id'}

    upload_caption(mock_youtube, "video_id", "en", "/tmp/file.srt", dry_run=False)

    # Assert that the insert method was called correctly
    mock_youtube.captions.return_value.insert.assert_called_once_with(
        part="snippet",
        body={'snippet': {'videoId': 'video_id', 'language': 'en', 'isDraft': False}},
        media_body=mock_media_file_upload.return_value
    )

def test_delete_caption_dry_run():
    """Tests that delete_caption in dry run mode does not call the API."""
    mock_youtube = Mock()
    delete_caption(mock_youtube, "caption_id", dry_run=True)
    mock_youtube.captions().delete.assert_not_called()

def test_delete_caption_live_run():
    """Tests that delete_caption in live mode calls the API."""
    mock_youtube = Mock()
    delete_caption(mock_youtube, "caption_id", dry_run=False)
    mock_youtube.captions().delete.assert_called_once_with(id="caption_id")