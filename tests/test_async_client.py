from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

from minimax import AsyncMinimax
from minimax.exceptions import MinimaxAPIError
from minimax.types import FileResponse, VideoGenerationResponse


@pytest_asyncio.fixture
async def client(api_key, group_id):
    async with AsyncMinimax(api_key=api_key, group_id=group_id) as client:
        yield client


@pytest.mark.asyncio
async def test_text_to_video_success(client, mock_async_response):
    with patch.object(client._client, "post", return_value=mock_async_response), patch.object(
        client._client, "get", return_value=mock_async_response
    ):  # For polling
        response = await client.text_to_video("A beautiful sunset", wait_for_completion=True)
        assert isinstance(response, VideoGenerationResponse)
        assert response.task_id == "test_task_id"
        assert response.file_id == "test_file_id"


@pytest.mark.asyncio
async def test_text_to_video_error(client, mock_async_error_response):
    with patch.object(client._client, "post", return_value=mock_async_error_response):
        with pytest.raises(MinimaxAPIError):
            await client.text_to_video("A beautiful sunset")


@pytest.mark.asyncio
async def test_image_to_video_success(client, mock_async_response, test_image):
    with patch.object(client._client, "post", return_value=mock_async_response), patch.object(
        client._client, "get", return_value=mock_async_response
    ):  # For polling
        response = await client.image_to_video(test_image, text="Make it dramatic", wait_for_completion=True)
        assert isinstance(response, VideoGenerationResponse)
        assert response.task_id == "test_task_id"
        assert response.file_id == "test_file_id"


@pytest.mark.asyncio
async def test_image_to_video_error(client, mock_async_error_response, test_image):
    with patch.object(client._client, "post", return_value=mock_async_error_response):
        with pytest.raises(MinimaxAPIError):
            await client.image_to_video(test_image, text="Make it dramatic")


@pytest.mark.asyncio
async def test_retrieve_video_success(client, mock_async_response):
    with patch.object(client._client, "get", return_value=mock_async_response):
        response = await client.retrieve_video("test_file_id")
        assert isinstance(response, FileResponse)
        assert response.file_id == "test_file_id"
        assert response.filename == "test.mp4"
        assert response.download_url == "https://example.com/test.mp4"


@pytest.mark.asyncio
async def test_retrieve_video_error(client, mock_async_error_response):
    with patch.object(client._client, "get", return_value=mock_async_error_response):
        with pytest.raises(MinimaxAPIError):
            await client.retrieve_video("test_file_id")


@pytest.mark.asyncio
async def test_generate_video(client: AsyncMinimax, tmp_path: Path):
    """Test generating a video from text"""
    download_path = tmp_path / "test_video.mp4"

    with patch("minimax.client.AsyncMinimax.text_to_video") as mock_text_to_video, patch(
        "minimax.client.AsyncMinimax.retrieve_video"
    ) as mock_retrieve_video:
        mock_text_to_video.return_value = VideoGenerationResponse(task_id="123", file_id="456")
        result = await client.generate_video(text="A beautiful sunset", download_path=str(download_path))
        assert str(download_path) == result  # generate_video returns the download path
        mock_retrieve_video.assert_called_once_with(file_id="456", download_path=str(download_path))


@pytest.mark.asyncio
async def test_generate_video_no_input_error(client):
    with pytest.raises(ValueError):
        await client.generate_video()
