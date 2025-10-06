import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.file_handler import download_channel_captions_to_csv, process_csv_batch, generate_wide_report

@pytest.fixture
def mock_youtube_api():
    """Fixture to mock the YouTube API client."""
    return MagicMock()

@patch('src.file_handler.list_captions')
@patch('src.file_handler.get_channel_videos')
def test_download_channel_captions_to_csv(mock_get_channel_videos, mock_list_captions, mock_youtube_api, tmp_path):
    """
    Test downloading channel captions to a CSV file.
    """
    # Arrange
    channel_id = "UC1234567890"
    channel_nickname = "test_channel"
    csv_path = tmp_path / f"captions_{channel_nickname}.csv"

    mock_get_channel_videos.return_value = [
        {'id': 'video1', 'title': 'Test Video 1'},
        {'id': 'video2', 'title': 'Test Video 2'}
    ]

    # Mock the captions list response
    mock_list_captions.side_effect = [
        {
            'items': [
                {'id': 'caption1', 'snippet': {'language': 'en'}}
            ]
        },
        {
            'items': []
        }
    ]

    # Act
    os.chdir(tmp_path)
    download_channel_captions_to_csv(mock_youtube_api, channel_id, channel_nickname)

    # Assert
    assert os.path.exists(csv_path)
    df = pd.read_csv(csv_path)

    assert len(df) == 2
    assert df.iloc[0]['video_id'] == 'video1'
    assert df.iloc[0]['caption_id'] == 'caption1'
    assert df.iloc[1]['video_id'] == 'video2'
    assert pd.isna(df.iloc[1]['caption_id'])

    mock_get_channel_videos.assert_called_once_with(mock_youtube_api, channel_id)
    assert mock_list_captions.call_count == 2


@patch('src.file_handler.list_captions')
@patch('src.file_handler.get_channel_videos')
def test_generate_wide_report(mock_get_channel_videos, mock_list_captions, mock_youtube_api, tmp_path):
    """
    Test generating a wide format report of subtitle availability.
    """
    # Arrange
    channel_id = "UC1234567890"
    channel_nickname = "test_channel"
    report_path = tmp_path / f"report_{channel_nickname}.csv"

    mock_get_channel_videos.return_value = [
        {'id': 'video1', 'title': 'Test Video 1'},
        {'id': 'video2', 'title': 'Test Video 2'}
    ]

    mock_list_captions.side_effect = [
        {
            'items': [
                {'id': 'caption1_en', 'snippet': {'language': 'en'}},
                {'id': 'caption1_fr', 'snippet': {'language': 'fr'}}
            ]
        },
        {
            'items': [
                {'id': 'caption2_en', 'snippet': {'language': 'en'}}
            ]
        }
    ]

    # Act
    os.chdir(tmp_path)
    generate_wide_report(mock_youtube_api, channel_id, channel_nickname)

    # Assert
    assert os.path.exists(report_path)
    df = pd.read_csv(report_path)

    assert len(df) == 2
    assert 'caption_id_en' in df.columns
    assert 'caption_id_fr' in df.columns
    assert df.iloc[0]['caption_id_en'] == 'caption1_en'
    assert df.iloc[0]['caption_id_fr'] == 'caption1_fr'
    assert df.iloc[1]['caption_id_en'] == 'caption2_en'
    assert pd.isna(df.iloc[1]['caption_id_fr'])


@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
def test_process_csv_batch(mock_delete, mock_update, mock_upload, mock_youtube_api, tmp_path):
    """
    Test processing a CSV batch file with UPLOAD, UPDATE, and DELETE actions.
    """
    # Arrange
    csv_path = tmp_path / "batch.csv"
    data = {
        'video_id': ['video1', 'video2', 'video3'],
        'language': ['en', 'fr', 'de'],
        'action': ['UPLOAD', 'UPDATE', 'DELETE'],
        'file_path': ['/path/to/en.srt', '/path/to/fr.srt', ''],
        'caption_id': ['', 'caption2', 'caption3']
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    # Act
    process_csv_batch(mock_youtube_api, csv_path)

    # Assert
    mock_upload.assert_called_once_with(mock_youtube_api, 'video1', 'en', '/path/to/en.srt')
    mock_update.assert_called_once_with(mock_youtube_api, 'video2', 'fr', '/path/to/fr.srt', caption_id='caption2')
    mock_delete.assert_called_once_with(mock_youtube_api, 'caption3')