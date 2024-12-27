"""Exceptions for the Minimax SDK."""

from typing import Any, Optional, Union


class MinimaxError(Exception):
    """Base exception class for all Minimax SDK errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class MinimaxAPIError(MinimaxError):
    """Exception raised when the Minimax API returns an error response.

    Attributes:
        message: A human-readable error message
        status_code: The HTTP status code returned by the API
        response: The full response data from the API
        base_resp: The base_resp object containing status_code and status_msg
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Union[dict, str]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

        # Handle both dict and string responses
        if isinstance(response, dict):
            self.base_resp = response.get("base_resp", {})
            self.api_status_code = self.base_resp.get("status_code")
            self.api_status_msg = self.base_resp.get("status_msg")
        else:
            self.base_resp = {}
            self.api_status_code = None
            self.api_status_msg = None

        # Enhance message with additional details
        details = [message]
        if self.status_code:
            details.append(f"HTTP Status: {self.status_code}")
        if self.api_status_code:
            details.append(f"API Status: {self.api_status_code}")
        if self.api_status_msg:
            details.append(f"API Message: {self.api_status_msg}")

        self.message = " | ".join(details)


class MinimaxAuthError(MinimaxAPIError):
    """Exception raised for authentication errors (invalid API key, etc)."""

    pass


class MinimaxRateLimitError(MinimaxAPIError):
    """Exception raised when API rate limits are exceeded."""

    pass


class MinimaxTimeoutError(MinimaxAPIError):
    """Exception raised when a request times out."""

    pass


class MinimaxValidationError(MinimaxError):
    """Exception raised for invalid input parameters."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        if field:
            self.message = f"{message} (field: {field}, value: {value})"
