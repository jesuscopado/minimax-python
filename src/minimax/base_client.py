import asyncio
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Dict, Optional, Type, TypeVar, Union

import httpx
from dotenv import load_dotenv

from .exceptions import (
    MinimaxAPIError,
    MinimaxAuthError,
    MinimaxError,
    MinimaxRateLimitError,
    MinimaxTimeoutError,
    MinimaxValidationError,
)
from .types import VideoGenerationResponse, VideoGenerationStatus
from .utils import encode_image_to_base64

T = TypeVar("T", bound="BaseClient")

# Configure logging
logger = logging.getLogger("minimax")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Load environment variables from .env file
load_dotenv()


class BaseClient:
    """Base class with shared utilities for Minimax API clients.

    This class provides common functionality for both synchronous and asynchronous
    clients, including authentication, configuration, and resource management.

    Args:
        api_key: The Minimax API key. If not provided, will look for MINIMAX_API_KEY env var.
        group_id: The Minimax group ID. If not provided, will look for MINIMAX_GROUP_ID env var.
        timeout: Request timeout in seconds. Default is 10.0.
        max_retries: Maximum number of retries for failed requests. Default is 3.
        retry_delay: Delay between retries in seconds. Default is 1.0.
        poll_interval: Interval between polling attempts in seconds. Default is 1.0.
        log_interval: Interval between status log messages in seconds. Default is 30.0.

    Raises:
        ValueError: If api_key or group_id is not provided and not found in environment.
    """

    BASE_URL = "https://api.minimaxi.chat/v1"
    BASE64_PATTERN = re.compile(r"^data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/]+=*$")

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        poll_interval: float = 1.0,
        log_interval: float = 30.0,
    ):
        self._api_key = api_key or os.getenv("MINIMAX_API_KEY")
        if not self._api_key:
            logger.error("API key not provided in constructor or environment")
            raise ValueError(
                "API key must be provided either through constructor or MINIMAX_API_KEY environment variable"
            )

        self._group_id = group_id or os.getenv("MINIMAX_GROUP_ID")
        if not self._group_id:
            logger.error("Group ID not provided in constructor or environment")
            raise ValueError(
                "Group ID must be provided either through constructor or MINIMAX_GROUP_ID environment variable"
            )

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.poll_interval = poll_interval
        self.log_interval = log_interval

        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(timeout={timeout}s, max_retries={max_retries}, poll_interval={poll_interval}s)"
        )

    @property
    def api_key(self) -> str:
        """The Minimax API key being used."""
        return self._api_key

    @property
    def group_id(self) -> str:
        """The Minimax group ID being used."""
        return self._group_id

    def _get_headers(self) -> Dict[str, str]:
        """Get base headers for all requests.

        Returns:
            Dict containing Authorization and Content-Type headers.
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _prepare_image(self, image: Union[str, Path, bytes]) -> str:
        """Prepare image data for API requests.

        Handles various input formats:
        - Base64 encoded strings
        - URLs (http/https)
        - File paths
        - Raw bytes

        Args:
            image: The image data in one of the supported formats.

        Returns:
            str: The image data in the format expected by the API.
        """
        logger.debug(f"Preparing image input of type: {type(image)}")
        if isinstance(image, str) and self.BASE64_PATTERN.match(image):
            logger.debug("Image is already in base64 format")
            return image
        elif isinstance(image, str) and image.startswith(("http://", "https://")):
            logger.debug("Image is a URL")
            return image
        elif isinstance(image, bytes):
            logger.debug("Converting bytes to base64")
            import base64

            try:
                encoded = base64.b64encode(image).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"
            except Exception as e:
                raise MinimaxValidationError(
                    f"Failed to encode image bytes: {e}",
                    field="image",
                    value=type(image).__name__,
                )
        else:
            logger.debug("Converting image file to base64")
            try:
                return encode_image_to_base64(image)
            except Exception as e:
                raise MinimaxValidationError(
                    f"Failed to read or encode image file: {e}",
                    field="image",
                    value=str(image),
                )

    def _prepare_download_path(self, download_path: Optional[str] = None) -> str:
        """Prepare the download path for the video file.

        Args:
            download_path: Optional custom path for the output file.

        Returns:
            str: The prepared download path
        """
        if download_path:
            logger.debug(f"Using provided download path: {download_path}")
            return download_path

        # Generate a default path if none provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"minimax_video_{timestamp}.mp4"

    async def _handle_api_error(
        self,
        response: Union[httpx.Response, dict],
        operation: str = "API request",
    ) -> None:
        """Handle API errors consistently.

        Args:
            response: The API response to check for errors.
            operation: Description of the operation being performed.

        Raises:
            MinimaxAPIError: With appropriate error details.
        """
        try:
            if isinstance(response, dict):
                data = response
                status_code = data.get("base_resp", {}).get("status_code", 0)
            else:
                status_code = response.status_code
                data = response.json() if response.status_code != 204 else {}

            base_resp = data.get("base_resp", {})
            api_status_code = base_resp.get("status_code", 0)

            if api_status_code != 0 or status_code != 200:
                error_msg = base_resp.get("status_msg", "Unknown error")
                logger.error(f"{operation} failed: {error_msg}")

                # Map status codes to specific exceptions
                if status_code == 401 or status_code == 403:
                    raise MinimaxAuthError(
                        f"Authentication failed: {error_msg}",
                        status_code=status_code,
                        response=data,
                    )
                elif status_code == 429:
                    raise MinimaxRateLimitError(
                        f"Rate limit exceeded: {error_msg}",
                        status_code=status_code,
                        response=data,
                    )
                else:
                    raise MinimaxAPIError(
                        f"{operation} failed: {error_msg}",
                        status_code=status_code,
                        response=data,
                    )

        except MinimaxError:
            raise
        except httpx.TimeoutException as e:
            raise MinimaxTimeoutError(
                f"Request timed out: {e}",
                status_code=None,
                response=str(e),
            )
        except Exception as e:
            if not isinstance(e, MinimaxError):
                logger.error(f"Unexpected error during {operation}: {e}")
                raise MinimaxAPIError(
                    f"Unexpected error during {operation}: {e}",
                    status_code=getattr(response, "status_code", None),
                    response=str(e),
                )

    def _handle_polling_status(
        self,
        *,
        status: VideoGenerationStatus,
        task_id: str,
        attempts: int,
        elapsed: float,
        current_time: float,
        last_log_time: float,
    ) -> tuple[bool, float]:
        """Handle polling status and logging logic.

        Args:
            status: Current video generation status
            task_id: Task ID being polled
            attempts: Number of polling attempts so far
            elapsed: Time elapsed since polling started
            current_time: Current timestamp
            last_log_time: Last time a status was logged

        Returns:
            Tuple of (should_continue_polling, new_last_log_time)

        Raises:
            MinimaxAPIError: If the video generation failed
        """
        if status == VideoGenerationStatus.SUCCESS:
            if attempts == 1:
                logger.info(f"Task {task_id} is already completed")
            else:
                logger.info(f"Task {task_id} completed after {int(elapsed)}s")
            return False, last_log_time
        elif status == VideoGenerationStatus.FAILED:
            error_msg = f"Video generation failed after {int(elapsed)}s"
            logger.error(error_msg)
            raise MinimaxAPIError(error_msg, status_code=None, response={"status": status.value})

        # Only log status periodically to avoid spam
        if attempts == 1:
            logger.info(f"Task status: {status.value}, starting to wait...")
            return True, last_log_time
        elif current_time - last_log_time >= self.log_interval:
            logger.info(f"Still waiting... (status: {status.value}, elapsed: {int(elapsed)}s)")
            return True, current_time
        else:
            logger.debug(f"Current status: {status.value} (elapsed: {int(elapsed)}s)")
            return True, last_log_time

    def _handle_polling_response(
        self,
        status_response: Union[httpx.Response, dict],
    ) -> tuple[VideoGenerationStatus, dict]:
        """Handle and parse polling response.

        Args:
            status_response: Raw response from polling request

        Returns:
            Tuple of (status, parsed_data)

        Raises:
            MinimaxAPIError: If response parsing fails
        """
        if isinstance(status_response, dict):
            data = status_response
        elif isinstance(status_response, httpx.Response):
            data = status_response.json()
        else:
            raise MinimaxAPIError(
                f"Unexpected response type: {type(status_response)}",
                response=str(status_response),
            )

        return VideoGenerationStatus(data["status"]), data


class SyncAPIClient(BaseClient):
    """Base class for synchronous operations"""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        timeout: Optional[float] = 10.0,
        httpx_client: Optional[httpx.Client] = None,
    ):
        super().__init__(api_key=api_key, group_id=group_id, timeout=timeout)
        self._client = httpx_client or httpx.Client(timeout=timeout)
        logger.debug("Initialized synchronous HTTP client")

    def _handle_generation_response(self, response: Union[httpx.Response, dict]) -> str:
        """Handle response from video generation endpoint (sync version)"""
        try:
            # Handle both pre-parsed JSON and raw responses
            if isinstance(response, dict):
                data = response
            else:
                data = response.json()

            # Check for API-level errors
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                error_msg = f"API Error: {base_resp.get('status_msg', 'Unknown error')}"
                logger.error(error_msg)
                raise MinimaxAPIError(
                    error_msg,
                    status_code=base_resp.get("status_code"),
                    response=data,
                )

            # Check for task_id
            task_id = data.get("task_id")
            if not task_id:
                logger.error(f"No task_id in response: {data}")
                raise MinimaxAPIError(
                    "No task_id in response",
                    status_code=getattr(response, "status_code", None),
                    response=data,
                )

            logger.info(f"Successfully initiated video generation with task_id: {task_id}")
            return task_id

        except MinimaxAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Raw response content: {getattr(response, 'text', str(response))}")
            raise MinimaxAPIError(
                "Failed to parse API response",
                status_code=getattr(response, "status_code", None),
                response=getattr(response, "text", str(response)),
            )

    def _poll_status(self, task_id: str) -> VideoGenerationResponse:
        """Synchronous polling for video generation status."""
        logger.info(f"Starting to poll for task: {task_id}")
        attempts = 0
        start_time = time.time()
        last_log_time = start_time

        while True:
            attempts += 1
            current_time = time.time()
            elapsed = current_time - start_time

            try:
                status_response = self._client.get(
                    f"{self.BASE_URL}/query/video_generation",
                    params={"task_id": task_id},
                    headers=self._get_headers(),
                )

                if status_response.status_code != 200:
                    logger.error(f"HTTP Error {status_response.status_code} while polling")
                    logger.error(f"Response headers: {dict(status_response.headers)}")
                    logger.error(f"Raw response content: {status_response.text}")
                    # For HTTP errors, we might want to retry quickly
                    if attempts >= self.max_retries:
                        raise MinimaxAPIError(
                            f"Failed to poll status: {status_response.text}",
                            status_code=status_response.status_code,
                            response=status_response.text,
                        )
                    time.sleep(1)  # Quick retry for HTTP errors
                    continue

                try:
                    status, data = self._handle_polling_response(status_response)
                    should_continue, new_last_log_time = self._handle_polling_status(
                        status=status,
                        task_id=task_id,
                        attempts=attempts,
                        elapsed=elapsed,
                        current_time=current_time,
                        last_log_time=last_log_time,
                    )

                    if should_continue:
                        last_log_time = new_last_log_time  # Update the last_log_time
                        time.sleep(self.poll_interval)
                    else:
                        return VideoGenerationResponse(**data)

                except Exception as e:
                    logger.error(f"Failed to parse polling response: {e}")
                    logger.error(f"Raw response content: {status_response.text}")
                    if attempts >= self.max_retries:
                        raise MinimaxAPIError(
                            "Failed to parse polling response",
                            status_code=status_response.status_code,
                            response=status_response.text,
                        )
                    time.sleep(1)  # Quick retry for parsing errors
                    continue

            except httpx.RequestError as e:
                logger.error(f"Network error while polling: {e}")
                if attempts >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached while polling task {task_id}")
                    if isinstance(e, httpx.TimeoutException):
                        raise MinimaxTimeoutError(
                            f"Polling timed out after {attempts} attempts: {e}",
                            status_code=None,
                            response=str(e),
                        )
                    else:
                        raise MinimaxAPIError(
                            f"Network error while polling: {e}",
                            status_code=0,
                            response=str(e),
                        )
                time.sleep(1)  # Quick retry for network errors

    def close(self):
        """Close the client session"""
        if self._client:
            logger.debug("Closing synchronous client session")
            self._client.close()

    def __enter__(self: T) -> T:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class AsyncAPIClient(BaseClient):
    """Base class for asynchronous operations"""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        timeout: Optional[float] = 10.0,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(api_key=api_key, group_id=group_id, timeout=timeout)
        self._client = httpx_client or httpx.AsyncClient(timeout=timeout)
        logger.debug("Initialized asynchronous HTTP client")

    async def _handle_generation_response(self, response: Union[httpx.Response, dict]) -> str:
        """Handle response from video generation endpoint (async version)"""
        try:
            # Handle both pre-parsed JSON and raw responses
            if isinstance(response, dict):
                data = response
            elif isinstance(response, httpx.Response):
                # Check status code first
                if response.status_code != 200:
                    logger.error(f"HTTP Error {response.status_code} from API")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Raw response content: {response.text}")
                    raise MinimaxAPIError(
                        f"Failed to generate video: {response.text}",
                        status_code=response.status_code,
                        response=response.text,
                    )

                # Get the JSON data
                data = response.json()

            # Check for API-level errors
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                error_msg = f"API Error: {base_resp.get('status_msg', 'Unknown error')}"
                logger.error(error_msg)
                raise MinimaxAPIError(
                    error_msg,
                    status_code=base_resp.get("status_code"),
                    response=data,
                )

            # Check for task_id
            task_id = data.get("task_id")
            if not task_id:
                logger.error(f"No task_id in response: {data}")
                raise MinimaxAPIError(
                    "No task_id in response",
                    status_code=getattr(response, "status_code", None),
                    response=data,
                )

            logger.info(f"Successfully initiated video generation with task_id: {task_id}")
            return task_id

        except MinimaxError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Raw response content: {getattr(response, 'text', str(response))}")
            raise MinimaxAPIError(
                "Failed to parse API response",
                status_code=getattr(response, "status_code", None),
                response=getattr(response, "text", str(response)),
            )

    async def _poll_status(self, task_id: str) -> VideoGenerationResponse:
        """Asynchronous polling for video generation status."""
        logger.info(f"Starting to poll for task: {task_id}")
        attempts = 0
        start_time = time.time()
        last_log_time = start_time

        while True:
            attempts += 1
            current_time = time.time()
            elapsed = current_time - start_time

            try:
                status_response = await self._client.get(
                    f"{self.BASE_URL}/query/video_generation",
                    params={"task_id": task_id},
                    headers=self._get_headers(),
                )

                if status_response.status_code != 200:
                    logger.error(f"HTTP Error {status_response.status_code} while polling")
                    logger.error(f"Response headers: {dict(status_response.headers)}")
                    logger.error(f"Raw response content: {status_response.text}")
                    # For HTTP errors, we might want to retry quickly
                    if attempts >= self.max_retries:
                        raise MinimaxAPIError(
                            f"Failed to poll status: {status_response.text}",
                            status_code=status_response.status_code,
                            response=status_response.text,
                        )
                    await asyncio.sleep(1)  # Quick retry for HTTP errors
                    continue

                try:
                    status, data = self._handle_polling_response(status_response)
                    should_continue, new_last_log_time = self._handle_polling_status(
                        status=status,
                        task_id=task_id,
                        attempts=attempts,
                        elapsed=elapsed,
                        current_time=current_time,
                        last_log_time=last_log_time,
                    )

                    if should_continue:
                        last_log_time = new_last_log_time  # Update the last_log_time
                        await asyncio.sleep(self.poll_interval)
                    else:
                        return VideoGenerationResponse(**data)

                except Exception as e:
                    logger.error(f"Failed to parse polling response: {e}")
                    logger.error(f"Raw response content: {status_response.text}")
                    if attempts >= self.max_retries:
                        raise MinimaxAPIError(
                            "Failed to parse polling response",
                            status_code=status_response.status_code,
                            response=status_response.text,
                        )
                    await asyncio.sleep(1)  # Quick retry for parsing errors
                    continue

            except httpx.RequestError as e:
                logger.error(f"Network error while polling: {e}")
                if attempts >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached while polling task {task_id}")
                    if isinstance(e, httpx.TimeoutException):
                        raise MinimaxTimeoutError(
                            f"Polling timed out after {attempts} attempts: {e}",
                            status_code=None,
                            response=str(e),
                        )
                    else:
                        raise MinimaxAPIError(
                            f"Network error while polling: {e}",
                            status_code=0,
                            response=str(e),
                        )
                await asyncio.sleep(1)  # Quick retry for network errors

    async def close(self):
        """Close the client session"""
        if self._client:
            logger.debug("Closing asynchronous client session")
            await self._client.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    def __del__(self) -> None:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except Exception:
            pass
