import pytest
from unittest.mock import patch, MagicMock
from src.main import main

@pytest.fixture
def mock_dependencies():
    """Fixture to mock all external dependencies of main."""
    with patch('src.main.load_config') as mock_load_config, \
         patch('src.main.get_authenticated_service') as mock_get_authenticated_service, \
         patch('src.main.download_channel_captions_to_csv') as mock_download, \
         patch('src.main.generate_wide_report') as mock_report, \
         patch('src.main.process_csv_batch') as mock_process, \
         patch('src.main.upload_caption') as mock_upload:

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
            "youtube_service": mock_youtube_service
        }

def test_main_download_command(mock_dependencies):
    """
    Test the 'download' command.
    """
    # Arrange
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'download']):
        # Act
        main()

        # Assert
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel")
        mock_dependencies["download"].assert_called_once_with(
            mock_dependencies["youtube_service"],
            "UC1234567890",
            "test_channel"
        )

def test_main_process_command(mock_dependencies):
    """
    Test the 'process' command.
    """
    # Arrange
    csv_path = "/path/to/batch.csv"
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'process', '--csv-path', csv_path]):
        # Act
        main()

        # Assert
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel")
        mock_dependencies["process"].assert_called_once_with(
            mock_dependencies["youtube_service"],
            csv_path
        )

def test_main_upload_command(mock_dependencies):
    """
    Test the 'upload' command.
    """
    # Arrange
    video_id = "video1"
    language = "en"
    file_path = "/path/to/caption.srt"
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'upload', '--video-id', video_id, '--language', language, '--file-path', file_path]):
        # Act
        main()

        # Assert
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel")
        mock_dependencies["upload"].assert_called_once_with(
            mock_dependencies["youtube_service"],
            video_id,
            language,
            file_path
        )

@patch('os.path.exists', return_value=True)
@patch('os.access', return_value=True)
def test_main_smart_upload_command(mock_access, mock_exists, mock_dependencies):
    """
    Test the 'smart-upload' command.
    """
    # Arrange
    file1 = "/tmp/video1_en.srt"
    file2 = "/tmp/video1_fr.srt"
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'smart-upload', file1, file2]):
        # Act
        main()

        # Assert
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel")

        # Check that upload_caption was called twice
        assert mock_dependencies["upload"].call_count == 2

        # Check the calls to upload_caption
        mock_dependencies["upload"].assert_any_call(
            mock_dependencies["youtube_service"],
            'video1', 'en', file1
        )
        mock_dependencies["upload"].assert_any_call(
            mock_dependencies["youtube_service"],
            'video1', 'fr', file2
        )

def test_main_report_command(mock_dependencies):
    """
    Test the 'report' command.
    """
    # Arrange
    with patch('sys.argv', ['yousub', '-c', 'test_channel', 'report']):
        # Act
        main()

        # Assert
        mock_dependencies["get_authenticated_service"].assert_called_once_with("test_channel")
        mock_dependencies["report"].assert_called_once_with(
            mock_dependencies["youtube_service"],
            "UC1234567890",
            "test_channel"
        )