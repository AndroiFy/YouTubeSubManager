import pytest
from unittest.mock import MagicMock, patch
from src.youtube_api import get_channel_videos, upload_caption, update_caption, delete_caption

@pytest.fixture
def mock_youtube_api():
    """Fixture to mock the YouTube API client."""
    return MagicMock()

def test_get_channel_videos_pagination(mock_youtube_api):
    """
    Test that get_channel_videos correctly handles pagination.
    """
    # Arrange
    channel_id = "UC1234567890"

    # Mock the channels().list() response to get the uploads playlist ID
    mock_youtube_api.channels.return_value.list.return_value.execute.return_value = {
        'items': [{'contentDetails': {'relatedPlaylists': {'uploads': 'PL1234567890'}}}]
    }

    # Mock the playlistItems().list() response with two pages
    mock_youtube_api.playlistItems.return_value.list.return_value.execute.side_effect = [
        {
            'items': [
                {'snippet': {'resourceId': {'videoId': 'video1'}, 'title': 'Title 1'}},
                {'snippet': {'resourceId': {'videoId': 'video2'}, 'title': 'Title 2'}}
            ],
            'nextPageToken': 'page2'
        },
        {
            'items': [
                {'snippet': {'resourceId': {'videoId': 'video3'}, 'title': 'Title 3'}}
            ]
        }
    ]

    # Act
    videos = get_channel_videos(mock_youtube_api, channel_id)

    # Assert
    assert len(videos) == 3
    assert videos[0]['id'] == 'video1'
    assert videos[2]['id'] == 'video3'
    assert mock_youtube_api.playlistItems.return_value.list.call_count == 2

@patch('src.youtube_api.MediaFileUpload')
def test_upload_caption(mock_media_file_upload, mock_youtube_api):
    """
    Test uploading a caption.
    """
    # Arrange
    video_id = "video1"
    language = "en"
    file_path = "/path/to/caption.srt"

    mock_youtube_api.captions.return_value.insert.return_value.execute.return_value = {
        'id': 'new_caption_id'
    }

    # Act
    upload_caption(mock_youtube_api, video_id, language, file_path)

    # Assert
    mock_media_file_upload.assert_called_once_with(file_path, chunksize=-1, resumable=True)

    mock_youtube_api.captions.return_value.insert.assert_called_once()

    # Get the actual arguments from the call
    _, kwargs = mock_youtube_api.captions.return_value.insert.call_args
    assert kwargs['body']['snippet']['videoId'] == video_id
    assert kwargs['body']['snippet']['language'] == language

@patch('src.youtube_api.MediaFileUpload')
def test_update_caption_with_id(mock_media_file_upload, mock_youtube_api):
    """
    Test updating a caption when a valid caption_id is provided.
    """
    # Arrange
    video_id = "video1"
    language = "en"
    file_path = "/path/to/caption.srt"
    caption_id = "existing_caption_id"

    # Act
    update_caption(mock_youtube_api, video_id, language, file_path, caption_id)

    # Assert
    mock_media_file_upload.assert_called_once_with(file_path, chunksize=-1, resumable=True)
    mock_youtube_api.captions.return_value.update.assert_called_once()

    _, kwargs = mock_youtube_api.captions.return_value.update.call_args
    assert kwargs['body']['id'] == caption_id

@patch('src.youtube_api.list_captions')
@patch('src.youtube_api.MediaFileUpload')
@patch('src.youtube_api.upload_caption')
def test_update_caption_no_id_found_by_lang(mock_upload_caption, mock_media_file_upload, mock_list_captions, mock_youtube_api):
    """
    Test updating a caption when no caption_id is provided, and a matching caption is found by language.
    """
    # Arrange
    video_id = "video1"
    language = "en"
    file_path = "/path/to/caption.srt"

    # Mock the list response to return a caption with the matching language
    mock_list_captions.return_value = {
        'items': [
            {'id': 'found_caption_id', 'snippet': {'language': 'en'}}
        ]
    }

    # Act
    update_caption(mock_youtube_api, video_id, language, file_path, caption_id=None)

    # Assert
    mock_list_captions.assert_called_once_with(mock_youtube_api, video_id)
    mock_youtube_api.captions.return_value.update.assert_called_once()

    _, kwargs = mock_youtube_api.captions.return_value.update.call_args
    assert kwargs['body']['id'] == 'found_caption_id'

    # Ensure upload_caption was NOT called
    mock_upload_caption.assert_not_called()

@patch('src.youtube_api.list_captions')
@patch('src.youtube_api.MediaFileUpload')
@patch('src.youtube_api.upload_caption')
def test_update_caption_no_id_no_lang_match(mock_upload_caption, mock_media_file_upload, mock_list_captions, mock_youtube_api):
    """
    Test updating a caption when no caption_id is provided and no matching caption is found by language.
    This should result in a new caption being uploaded.
    """
    # Arrange
    video_id = "video1"
    language = "en"
    file_path = "/path/to/caption.srt"

    # Mock the list response to return no matching captions
    mock_list_captions.return_value = {
        'items': [
            {'id': 'other_caption', 'snippet': {'language': 'fr'}}
        ]
    }

    # Act
    update_caption(mock_youtube_api, video_id, language, file_path, caption_id=None)

    # Assert
    mock_list_captions.assert_called_once_with(mock_youtube_api, video_id)

    # Ensure update was NOT called, but upload was.
    mock_youtube_api.captions.return_value.update.assert_not_called()
    mock_upload_caption.assert_called_once_with(mock_youtube_api, video_id, language, file_path)

def test_delete_caption(mock_youtube_api):
    """
    Test deleting a caption.
    """
    # Arrange
    caption_id = "caption_to_delete"

    # Act
    delete_caption(mock_youtube_api, caption_id)

    # Assert
    mock_youtube_api.captions.return_value.delete.assert_called_once_with(id=caption_id)