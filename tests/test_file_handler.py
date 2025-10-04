import pytest
import pandas as pd
import io
from unittest.mock import Mock, patch
from src.file_handler import download_channel_captions_to_csv, process_csv_batch
from src.translations import load_translations

# Load translations for the test
load_translations('en')

@patch('src.file_handler.get_channel_videos')
@patch('pandas.DataFrame.to_csv')
def test_download_captions_uses_cache(mock_to_csv, mock_get_videos):
    """Tests that the download function calls get_channel_videos with the correct cache flag."""
    mock_youtube = Mock()
    mock_get_videos.return_value = []

    # First call, no_cache=False
    download_channel_captions_to_csv(mock_youtube, "channel_id", "nickname", no_cache=False)
    mock_get_videos.assert_called_with(mock_youtube, "channel_id", no_cache=False)

    # Second call, no_cache=True
    download_channel_captions_to_csv(mock_youtube, "channel_id", "nickname", no_cache=True)
    mock_get_videos.assert_called_with(mock_youtube, "channel_id", no_cache=True)

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('builtins.input', return_value='n')
def test_process_csv_quota_aborts(mock_input, mock_delete, mock_update, mock_upload):
    """Tests that the quota estimation prompt aborts the process if the user says no."""
    mock_youtube = Mock()
    csv_data = "video_id,action\nvid1,UPLOAD\nvid2,DELETE"

    with patch('pandas.read_csv', return_value=pd.read_csv(io.StringIO(csv_data))):
        process_csv_batch(mock_youtube, "dummy.csv")

    mock_upload.assert_not_called()
    mock_update.assert_not_called()
    mock_delete.assert_not_called()

@patch('src.file_handler.upload_caption')
@patch('src.file_handler.update_caption')
@patch('src.file_handler.delete_caption')
@patch('builtins.input', return_value='y')
def test_process_csv_quota_proceeds(mock_input, mock_delete, mock_update, mock_upload):
    """Tests that the quota estimation prompt proceeds if the user says yes."""
    mock_youtube = Mock()
    csv_data = "video_id,action\nvid1,UPLOAD\nvid2,DELETE"

    with patch('pandas.read_csv', return_value=pd.read_csv(io.StringIO(csv_data))):
        process_csv_batch(mock_youtube, "dummy.csv")

    mock_upload.assert_called_once()
    mock_delete.assert_called_once()
    mock_update.assert_not_called()