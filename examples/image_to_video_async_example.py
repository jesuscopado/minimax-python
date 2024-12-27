import os
import asyncio
from minimax import AsyncMinimax


async def main():
    # Initialize the async client
    client = AsyncMinimax(api_key=os.getenv("MINIMAX_API_KEY"))

    # Precise I2V Prompt Formula = Main Subject + Motion/Change + Camera Movement + Aesthetic Atmosphere
    prompt = """A cat in the scene runs quickly toward the camera, with white electric sparks 
    emanating from its eyes. Its entire body becomes surrounded by electricity as it runs 
    faster and faster. The scenery on both sides rushes backward rapidly, creating motion 
    blur that transforms into a glowing white time tunnel."""

    # Generate video from image asynchronously
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets/cat.jpeg")
    response = await client.image_to_video(image=image_path, text=prompt, wait_for_completion=True)
    print(f"Generated video file ID: {response.file_id}")

    # Download the video
    file_info = await client.retrieve_video(file_id=response.file_id, download_path="output_video_async.mp4")
    print(f"Video downloaded to: output_video_async.mp4")


if __name__ == "__main__":
    asyncio.run(main())
