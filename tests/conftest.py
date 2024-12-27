import httpx
import pytest


class MockResponse(httpx.Response):
    def __init__(self, status_code=200, text="", content=b"", json_data=None, headers=None):
        self.status_code = status_code
        self._text = text
        self._content = content
        self._json_data = json_data or {}
        self.headers = headers or {}

    def json(self):
        return self._json_data

    def read(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def content(self):
        return self._content


class AsyncMockResponse(MockResponse):
    """Async version of MockResponse that adds async methods"""

    async def aread(self):
        return self._content

    async def aclose(self):
        pass


@pytest.fixture
def api_key():
    return "test_api_key"


@pytest.fixture
def group_id():
    return "test_group_id"


@pytest.fixture
def test_image(tmp_path):
    image_path = tmp_path / "test.jpg"
    # Create a minimal valid JPEG file
    with open(image_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9")
    return str(image_path)


@pytest.fixture
def response_data():
    """Common response data for both sync and async tests"""
    return {
        "task_id": "test_task_id",
        "status": "Success",
        "file_id": "test_file_id",
        "base_resp": {"status_code": 0, "status_msg": "success"},
        "file": {
            "file_id": "test_file_id",
            "bytes": 1024,
            "created_at": 1735255881,
            "filename": "test.mp4",
            "purpose": "video_generation",
            "download_url": "https://example.com/test.mp4",
        },
    }


@pytest.fixture
def error_data():
    """Common error response for both sync and async tests"""
    return {
        "base_resp": {"status_code": 1000, "status_msg": "error"},
        "error": "test error",
    }


@pytest.fixture
def mock_response(response_data):
    """Mock for synchronous httpx.Response"""
    return MockResponse(
        status_code=200,
        text="test response text",
        content=b"test video content",
        json_data=response_data,
        headers={"Content-Type": "application/json"},
    )


@pytest.fixture
def mock_error_response(error_data):
    """Synchronous error response mock"""
    return MockResponse(
        status_code=400,
        text="test error response",
        content=b"error content",
        json_data=error_data,
        headers={"Content-Type": "application/json"},
    )


@pytest.fixture
def mock_async_response(response_data):
    """Mock for asynchronous httpx.Response"""
    return AsyncMockResponse(
        status_code=200,
        text="test response text",
        content=b"test video content",
        json_data=response_data,
        headers={"Content-Type": "application/json"},
    )


@pytest.fixture
def mock_async_error_response(error_data):
    """Asynchronous error response mock"""
    return AsyncMockResponse(
        status_code=400,
        text="test error response",
        content=b"error content",
        json_data=error_data,
        headers={"Content-Type": "application/json"},
    )


@pytest.fixture
def mock_download_response():
    """Mock for video download responses (both sync and async)"""
    return AsyncMockResponse(
        status_code=200,
        text="test video content",
        content=b"test video content",
        headers={"Content-Type": "video/mp4"},
    )
