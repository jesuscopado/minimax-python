from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minimax import Minimax
from minimax.exceptions import MinimaxAPIError
from minimax.types import FileResponse, VideoGenerationResponse


@pytest.fixture
def client(api_key, group_id):
    return Minimax(api_key=api_key, group_id=group_id)


def test_text_to_video_success(client, mock_response):
    with patch.object(client._client, "post", return_value=mock_response), patch.object(
        client._client, "get", return_value=mock_response
    ):  # For polling
        response = client.text_to_video("A beautiful sunset", wait_for_completion=True)
        assert isinstance(response, VideoGenerationResponse)
        assert response.task_id == "test_task_id"
        assert response.file_id == "test_file_id"


def test_text_to_video_error(client, mock_error_response):
    with patch.object(client._client, "post", return_value=mock_error_response):
        with pytest.raises(MinimaxAPIError):
            client.text_to_video("A beautiful sunset")


def test_image_to_video_success(client, mock_response, test_image):
    with patch.object(client._client, "post", return_value=mock_response), patch.object(
        client._client, "get", return_value=mock_response
    ):  # For polling
        response = client.image_to_video(test_image, text="Make it dramatic", wait_for_completion=True)
        assert isinstance(response, VideoGenerationResponse)
        assert response.task_id == "test_task_id"
        assert response.file_id == "test_file_id"


def test_image_to_video_error(client, mock_error_response, test_image):
    with patch.object(client._client, "post", return_value=mock_error_response):
        with pytest.raises(MinimaxAPIError):
            client.image_to_video(test_image, text="Make it dramatic")


def test_retrieve_video_success(client, mock_response):
    with patch.object(client._client, "get", return_value=mock_response):
        response = client.retrieve_video("test_file_id")
        assert isinstance(response, FileResponse)
        assert response.file_id == "test_file_id"
        assert response.filename == "test.mp4"
        assert response.download_url == "https://example.com/test.mp4"


def test_retrieve_video_error(client, mock_response):
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.json.return_value = {"base_resp": {"status_code": 1000, "status_msg": "error"}}
    error_response.text = "error response text"
    with patch.object(client._client, "get", return_value=error_response):
        with pytest.raises(MinimaxAPIError):
            client.retrieve_video("test_file_id")


def test_generate_video(client: Minimax, tmp_path: Path):
    """Test generating a video from text"""
    download_path = tmp_path / "test_video.mp4"

    with patch("minimax.client.Minimax.text_to_video") as mock_text_to_video, patch(
        "minimax.client.Minimax.retrieve_video"
    ) as mock_retrieve_video:
        mock_text_to_video.return_value = VideoGenerationResponse(task_id="123", file_id="456")
        result = client.generate_video(text="A beautiful sunset", download_path=str(download_path))
        assert str(download_path) == result  # generate_video returns the download path
        mock_retrieve_video.assert_called_once_with(file_id="456", download_path=str(download_path))


def test_generate_video_no_input_error(client):
    with pytest.raises(ValueError):
        client.generate_video()
