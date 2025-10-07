import pytest
from unittest.mock import patch, MagicMock, ANY
from src.main import main

@pytest.fixture
def mock_dependencies():
    """Fixture to mock all external dependencies of main."""
    with patch('src.main.Translator') as mock_translator_class, \
         patch('src.main.load_config') as mock_load_config, \
         patch('src.main.get_authenticated_service') as mock_get_authenticated_service, \
         patch('src.main.download_channel_captions_to_csv') as mock_download, \
         patch('src.main.generate_wide_report') as mock_report, \
         patch('src.main.process_csv_batch') as mock_process, \
         patch('src.main.upload_caption') as mock_upload, \
         patch('src.main.create_project') as mock_create_project, \
         patch('src.main.sync_project') as mock_sync_project, \
         patch('src.main.display_quota_usage') as mock_display_quota:

        mock_translator_instance = MagicMock()
        mock_translator_instance.get.side_effect = lambda key, **kwargs: key
        mock_translator_class.return_value = mock_translator_instance

        mock_load_config.return_value = {
            "channels": {
                "test_channel": "UC1234567890"
            }
        }
        mock_youtube_service = MagicMock()
        mock_get_authenticated_service.return_value = mock_youtube_service

        yield {
            "load_config": mock_load_config,
            "get_authenticated_service": mock_get_authenticated_service,
            "download": mock_download,
            "report": mock_report,
            "process": mock_process,
            "upload": mock_upload,
            "create_project": mock_create_project,
            "sync_project": mock_sync_project,
            "youtube_service": mock_youtube_service
        }

def test_main_download_command(mock_dependencies):
    """
    Test the 'download' command.
    """
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'download']):
        main()
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel", ANY)
        mock_dependencies["download"].assert_called_once_with(
            mock_dependencies["youtube_service"], "UC1234567890", "test_channel", ANY
        )

def test_main_process_command(mock_dependencies):
    """
    Test the 'process' command.
    """
    csv_path = "/path/to/batch.csv"
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'process', '--csv-path', csv_path]):
        main()
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel", ANY)
        mock_dependencies["process"].assert_called_once_with(
            mock_dependencies["youtube_service"], csv_path, ANY
        )

def test_main_upload_command(mock_dependencies):
    """
    Test the 'upload' command.
    """
    video_id = "video1"
    language = "en"
    file_path = "/path/to/caption.srt"
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'upload', '--video-id', video_id, '--language', language, '--file-path', file_path]):
        main()
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel", ANY)
        mock_dependencies["upload"].assert_called_once_with(
            mock_dependencies["youtube_service"], video_id, language, file_path, ANY
        )

@patch('os.path.exists', return_value=True)
@patch('os.access', return_value=True)
def test_main_smart_upload_command(mock_access, mock_exists, mock_dependencies):
    """
    Test the 'smart-upload' command.
    """
    file1 = "/tmp/video1_en.srt"
    file2 = "/tmp/video1_fr.srt"
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'smart-upload', file1, file2]):
        main()
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel", ANY)
        assert mock_dependencies["upload"].call_count == 2
        mock_dependencies["upload"].assert_any_call(
            mock_dependencies["youtube_service"], 'video1', 'en', file1, ANY
        )
        mock_dependencies["upload"].assert_any_call(
            mock_dependencies["youtube_service"], 'video1', 'fr', file2, ANY
        )

def test_main_report_command(mock_dependencies):
    """
    Test the 'report' command.
    """
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'report']):
        main()
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel", ANY)
        mock_dependencies["report"].assert_called_once_with(
            mock_dependencies["youtube_service"], "UC1234567890", "test_channel", ANY
        )