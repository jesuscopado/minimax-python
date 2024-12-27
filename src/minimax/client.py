from pathlib import Path
from typing import Optional, Union
import logging
import httpx

from .base_client import AsyncAPIClient, SyncAPIClient
from .exceptions import MinimaxAPIError
from .types import FileResponse, VideoGenerationInput, VideoGenerationResponse

logger = logging.getLogger("minimax")


class Minimax(SyncAPIClient):
    """Synchronous Minimax client implementation"""

    def text_to_video(
        self,
        text: str,
        model: str = "video-01",
        prompt_optimizer: bool = True,
        callback_url: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> VideoGenerationResponse:
        """Generate a video from text description.

        This method generates a video based on a text description. It can
        optionally wait for the generation to complete.

        Args:
            text: Text description for the video (max 2000 chars)
            model: Model ID (default: "video-01")
            prompt_optimizer: Whether to optimize prompts (default: True)
            callback_url: Optional URL for status updates
            wait_for_completion: Whether to wait for generation (default: True)

        Returns:
            VideoGenerationResponse containing task_id and optionally file_id

        Raises:
            MinimaxAPIError: If the request or generation fails
        """
        logger.info(f"Generating video from text")
        logger.debug(f"Using model: {model}, prompt_optimizer: {prompt_optimizer}")

        input_data = VideoGenerationInput(
            model=model,
            prompt=text,
            prompt_optimizer=prompt_optimizer,
            callback_url=callback_url,
        )
        payload = input_data.model_dump(exclude_none=True)

        logger.debug("Sending video generation request")
        response = self._client.post(
            f"{self.BASE_URL}/video_generation",
            headers=self._get_headers(),
            json=payload,
        )

        task_id = self._handle_generation_response(response)

        if not wait_for_completion:
            logger.info("Returning without waiting for completion")
            return VideoGenerationResponse(task_id=task_id)

        return self._poll_status(task_id)

    def image_to_video(
        self,
        image: Union[str, Path, bytes],
        text: Optional[str] = None,
        model: str = "video-01",
        prompt_optimizer: bool = True,
        callback_url: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> VideoGenerationResponse:
        """Generate a video from an image, optionally guided by text"""
        logger.info("Generating video from image" + " with text guidance" if text else "")
        logger.debug(f"Using model: {model}, prompt_optimizer: {prompt_optimizer}")

        input_data = VideoGenerationInput(
            model=model,
            prompt=text,
            first_frame_image=self._prepare_image(image),
            prompt_optimizer=prompt_optimizer,
            callback_url=callback_url,
        )
        payload = input_data.model_dump(exclude_none=True)

        logger.debug("Sending video generation request")
        response = self._client.post(
            f"{self.BASE_URL}/video_generation",
            headers=self._get_headers(),
            json=payload,
        )

        task_id = self._handle_generation_response(response)

        if not wait_for_completion:
            logger.info("Returning without waiting for completion")
            return VideoGenerationResponse(task_id=task_id)

        return self._poll_status(task_id)

    def retrieve_video(
        self,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
        download_path: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> FileResponse:
        """Retrieve video information and optionally download the video.

        Args:
            file_id: The ID of the file to retrieve. Either file_id or task_id must be provided.
            task_id: The ID of the task to retrieve the video from. Will wait for task completion if needed.
            download_path: Optional path to download the video to.
            wait_for_completion: Whether to wait for task completion if task_id is provided.

        Returns:
            FileResponse containing video information

        Raises:
            ValueError: If neither file_id nor task_id is provided
            MinimaxAPIError: If the video cannot be retrieved
        """
        if not file_id and not task_id:
            raise ValueError("Either file_id or task_id must be provided")

        # If task_id is provided, wait for completion to get file_id
        if task_id:
            logger.info(f"Retrieving video from task: {task_id}")
            if wait_for_completion:
                task_result = self._poll_status(task_id)
                if not task_result.file_id:
                    raise MinimaxAPIError(
                        "Task completed but no file_id was returned",
                        response={"task_id": task_id},
                    )
                file_id = task_result.file_id
                logger.info(f"Task completed, using file_id: {file_id}")
            else:
                # Just check current status
                response = self._client.get(
                    f"{self.BASE_URL}/query/video_generation",
                    params={"task_id": task_id},
                    headers=self._get_headers(),
                )
                data = response.json()
                if data.get("status") == "Success" and data.get("file_id"):
                    file_id = data["file_id"]
                    logger.info(f"Task already completed, using file_id: {file_id}")
                else:
                    raise MinimaxAPIError(
                        f"Task not completed. Current status: {data.get('status')}",
                        response=data,
                    )

        # Now we should have a file_id
        logger.info(f"Retrieving video information for file_id: {file_id}")

        try:
            response = self._client.get(
                f"{self.BASE_URL}/files/retrieve",
                params={"GroupId": self.group_id, "file_id": file_id},
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                logger.error(f"HTTP Error {response.status_code} while retrieving video")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Raw response content: {response.text}")
                raise MinimaxAPIError(
                    f"Failed to retrieve video: {response.text}",
                    status_code=response.status_code,
                    response=response.text,
                )

            try:
                data = response.json()
                if not data.get("file"):
                    error_msg = f"File not found: {data.get('base_resp', {}).get('status_msg', 'Unknown error')}"
                    logger.error(error_msg)
                    raise MinimaxAPIError(
                        error_msg,
                        status_code=response.status_code,
                        response=data,
                    )

                file_info = FileResponse(**data["file"])
                logger.debug(f"Retrieved file info: {file_info}")
            except Exception as e:
                logger.error(f"Failed to parse video info response: {e}")
                logger.error(f"Raw response content: {response.text}")
                raise MinimaxAPIError(
                    "Failed to parse video info response",
                    status_code=response.status_code,
                    response=response.text,
                )

            if download_path:
                logger.info(f"Downloading video to: {download_path}")
                try:
                    download_response = self._client.get(file_info.download_url)
                    if download_response.status_code != 200:
                        logger.error(f"HTTP Error {download_response.status_code} while downloading video")
                        logger.error(f"Response headers: {dict(download_response.headers)}")
                        raise MinimaxAPIError("Failed to download video")

                    with open(download_path, "wb") as f:
                        f.write(download_response.content)
                    logger.info("Video downloaded successfully")
                except Exception as e:
                    logger.error(f"Error downloading video: {e}")
                    raise MinimaxAPIError(f"Failed to download video: {e}")

            return file_info
        except Exception as e:
            if not isinstance(e, MinimaxAPIError):
                logger.error(f"Unexpected error retrieving video: {e}")
                raise MinimaxAPIError(f"Unexpected error: {e}")
            raise

    def create_video(
        self,
        text: Optional[str] = None,
        image: Optional[Union[str, Path, bytes]] = None,
        output_path: Optional[str] = None,
        prompt_optimizer: bool = True,
    ) -> str:
        """Create and download a video in one step."""
        logger.info("Creating and downloading video in one step")
        output_path = self._prepare_output_path(output_path)

        if text and not image:
            logger.debug("Using text-to-video generation")
            response = self.text_to_video(text, prompt_optimizer=prompt_optimizer, wait_for_completion=True)
        elif image:
            logger.debug("Using image-to-video generation")
            response = self.image_to_video(
                image, text=text, prompt_optimizer=prompt_optimizer, wait_for_completion=True
            )
        else:
            error_msg = "Either text or image must be provided"
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.retrieve_video(file_id=response.file_id, download_path=output_path)
        logger.info(f"Video created and downloaded to: {output_path}")
        return output_path

    def close(self):
        """Close the client session"""
        if self._client:
            self._client.close()


class AsyncMinimax(AsyncAPIClient):
    """Asynchronous Minimax client implementation"""

    async def text_to_video(
        self,
        text: str,
        model: str = "video-01",
        prompt_optimizer: bool = True,
        callback_url: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> VideoGenerationResponse:
        """Generate a video from text description.

        This method generates a video based on a text description. It can
        optionally wait for the generation to complete.

        Args:
            text: Text description for the video (max 2000 chars)

            model: Model ID (default: "video-01")
            prompt_optimizer: Whether to optimize prompts (default: True)
            callback_url: Optional URL for status updates
            wait_for_completion: Whether to wait for generation (default: True)

        Returns:
            VideoGenerationResponse containing task_id and optionally file_id

        Raises:
            MinimaxAPIError: If the request or generation fails
        """
        logger.info(f"Generating video from text (length: {len(text)})")
        logger.debug(f"Using model: {model}, prompt_optimizer: {prompt_optimizer}")

        input_data = VideoGenerationInput(
            model=model,
            prompt=text,
            prompt_optimizer=prompt_optimizer,
            callback_url=callback_url,
        )
        payload = input_data.model_dump(exclude_none=True)

        logger.debug("Sending video generation request")
        response = await self._client.post(
            f"{self.BASE_URL}/video_generation",
            headers=self._get_headers(),
            json=payload,
        )

        task_id = await self._handle_generation_response(response)

        if not wait_for_completion:
            logger.info("Returning without waiting for completion")
            return VideoGenerationResponse(task_id=task_id)

        return await self._poll_status(task_id)

    async def image_to_video(
        self,
        image: Union[str, Path, bytes],
        text: Optional[str] = None,
        model: str = "video-01",
        prompt_optimizer: bool = True,
        callback_url: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> VideoGenerationResponse:
        """Generate a video from an image, optionally guided by text"""
        logger.info("Generating video from image" + (f" with text guidance (length: {len(text)})" if text else ""))
        logger.debug(f"Using model: {model}, prompt_optimizer: {prompt_optimizer}")

        input_data = VideoGenerationInput(
            model=model,
            prompt=text,
            first_frame_image=self._prepare_image(image),
            prompt_optimizer=prompt_optimizer,
            callback_url=callback_url,
        )
        payload = input_data.model_dump(exclude_none=True)

        logger.debug("Sending video generation request")
        response = await self._client.post(
            f"{self.BASE_URL}/video_generation",
            headers=self._get_headers(),
            json=payload,
        )

        task_id = await self._handle_generation_response(response)

        if not wait_for_completion:
            logger.info("Returning without waiting for completion")
            return VideoGenerationResponse(task_id=task_id)

        return await self._poll_status(task_id)

    async def retrieve_video(
        self,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
        download_path: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> FileResponse:
        """Retrieve video information and optionally download the video.

        Args:
            file_id: The ID of the file to retrieve. Either file_id or task_id must be provided.
            task_id: The ID of the task to retrieve the video from. Will wait for task completion if needed.
            download_path: Optional path to download the video to.
            wait_for_completion: Whether to wait for task completion if task_id is provided.

        Returns:
            FileResponse containing video information

        Raises:
            ValueError: If neither file_id nor task_id is provided
            MinimaxAPIError: If the video cannot be retrieved
        """
        if not file_id and not task_id:
            raise ValueError("Either file_id or task_id must be provided")

        # If task_id is provided, wait for completion to get file_id
        if task_id:
            logger.info(f"Retrieving video from task: {task_id}")
            if wait_for_completion:
                task_result = await self._poll_status(task_id)
                if not task_result.file_id:
                    raise MinimaxAPIError(
                        "Task completed but no file_id was returned",
                        response={"task_id": task_id},
                    )
                file_id = task_result.file_id
                logger.info(f"Task completed, using file_id: {file_id}")
            else:
                # Just check current status
                response = await self._client.get(
                    f"{self.BASE_URL}/query/video_generation",
                    params={"task_id": task_id},
                    headers=self._get_headers(),
                )
                data = response.json()  # Don't await - httpx handles this internally
                if data.get("status") == "Success" and data.get("file_id"):
                    file_id = data["file_id"]
                    logger.info(f"Task already completed, using file_id: {file_id}")
                else:
                    raise MinimaxAPIError(
                        f"Task not completed. Current status: {data.get('status')}",
                        response=data,
                    )

        # Now we should have a file_id
        logger.info(f"Retrieving video information for file_id: {file_id}")

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/files/retrieve",
                params={"GroupId": self.group_id, "file_id": file_id},
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                logger.error(f"HTTP Error {response.status_code} while retrieving video")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Raw response content: {response.text}")
                raise MinimaxAPIError(
                    f"Failed to retrieve video: {response.text}",
                    status_code=response.status_code,
                    response=response.text,
                )

            try:
                data = response.json()  # Don't await - httpx handles this internally

                # Check if file exists
                if not data.get("file"):
                    error_msg = f"File not found: {data.get('base_resp', {}).get('status_msg', 'Unknown error')}"
                    logger.error(error_msg)
                    raise MinimaxAPIError(
                        error_msg,
                        status_code=response.status_code,
                        response=data,
                    )

                # Parse file info
                file_info = FileResponse(**data["file"])
                logger.debug(f"Retrieved file info: {file_info}")

                # Download if path provided
                if download_path:
                    logger.info(f"Downloading video to: {download_path}")
                    try:
                        download_response = await self._client.get(file_info.download_url)
                        if download_response.status_code != 200:
                            logger.error(f"HTTP Error {download_response.status_code} while downloading video")
                            logger.error(f"Response headers: {dict(download_response.headers)}")
                            raise MinimaxAPIError(
                                "Failed to download video",
                                status_code=download_response.status_code,
                                response=download_response.text,
                            )

                        with open(download_path, "wb") as f:
                            f.write(await download_response.aread())
                        logger.info("Video downloaded successfully")
                    except Exception as e:
                        logger.error(f"Error downloading video: {e}")
                        raise MinimaxAPIError(
                            f"Failed to download video: {e}",
                            status_code=getattr(e, "status_code", None),
                            response=str(e),
                        )

                return file_info

            except MinimaxAPIError:
                raise
            except Exception as e:
                logger.error(f"Failed to process video info: {e}")
                logger.error(f"Raw response content: {response.text}")
                raise MinimaxAPIError(
                    f"Failed to process video info: {e}",
                    status_code=response.status_code,
                    response=response.text,
                )

        except MinimaxAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving video: {e}")
            raise MinimaxAPIError(
                f"Unexpected error retrieving video: {e}",
                response=str(e),
            )

    async def create_video(
        self,
        text: Optional[str] = None,
        image: Optional[Union[str, Path, bytes]] = None,
        output_path: Optional[str] = None,
        prompt_optimizer: bool = True,
    ) -> str:
        """Create and download a video in one step."""
        logger.info("Creating and downloading video in one step")
        output_path = self._prepare_output_path(output_path)

        if text and not image:
            logger.debug("Using text-to-video generation")
            response = await self.text_to_video(text, prompt_optimizer=prompt_optimizer, wait_for_completion=True)
        elif image:
            logger.debug("Using image-to-video generation")
            response = await self.image_to_video(
                image, text=text, prompt_optimizer=prompt_optimizer, wait_for_completion=True
            )
        else:
            error_msg = "Either text or image must be provided"
            logger.error(error_msg)
            raise ValueError(error_msg)

        await self.retrieve_video(file_id=response.file_id, download_path=output_path)
        logger.info(f"Video created and downloaded to: {output_path}")
        return output_path

    async def close(self):
        """Close the client session"""
        if self._client:
            await self._client.aclose()
