from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class VideoGenerationStatus(str, Enum):
    """Status of a video generation task.

    Attributes:
        PREPARING: The task is being prepared
        PROCESSING: The task is generating the video
        SUCCESS: The task completed successfully
        FAILED: The task failed
    """

    PREPARING = "Preparing"
    PROCESSING = "Processing"
    SUCCESS = "Success"
    FAILED = "Failed"


class VideoGenerationInput(BaseModel):
    """Input parameters for video generation."""

    model: str = Field(default="video-01", description="Model ID to use for generation")
    prompt: Optional[str] = Field(None, description="Text description for the video")
    first_frame_image: Optional[str] = Field(None, description="Base64 encoded image or URL")
    prompt_optimizer: bool = Field(default=True, description="Whether to optimize prompts")
    callback_url: Optional[str] = Field(None, description="URL for status updates")


class VideoGenerationResponse(BaseModel):
    """Response from video generation API."""

    task_id: str = Field(..., description="ID of the generation task")
    status: Optional[VideoGenerationStatus] = Field(None, description="Current status of the task")
    file_id: Optional[str] = Field(None, description="ID of the generated video file")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class FileResponse(BaseModel):
    """Response from file retrieval API."""

    file_id: Union[str, int] = Field(..., description="ID of the file (can be string or integer)")
    filename: str = Field(..., description="Name of the file")
    download_url: str = Field(..., description="URL to download the file")
    bytes: Optional[int] = Field(None, description="Size of the file in bytes")
    created_at: Optional[int] = Field(None, description="Creation timestamp")
    purpose: Optional[str] = Field(None, description="Purpose of the file")

    @field_validator("file_id", mode="before")
    @classmethod
    def validate_file_id(cls, v):
        """Convert integer file_id to string if needed."""
        if isinstance(v, int):
            return str(v)
        return v

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Convert datetime string to timestamp if needed."""
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except ValueError:
                pass
        return v
