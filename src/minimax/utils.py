import base64
import mimetypes
from pathlib import Path
from typing import Union


def encode_image_to_base64(image_path: Union[str, Path]) -> str:
    """
    Convert an image file to a base64 encoded string with proper mime type

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string with mime type prefix (e.g. "data:image/jpeg;base64,...")
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    mime_type = mimetypes.guess_type(image_path)[0]
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Invalid image file type: {image_path}")

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
