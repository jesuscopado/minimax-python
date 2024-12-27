import os
import asyncio
from minimax import AsyncMinimax


async def main():
    # Initialize the async client
    client = AsyncMinimax(api_key=os.getenv("MINIMAX_API_KEY"))

    # Precise Prompt Formula = Main Subject + Scene + Motion + Camera Movement + Aesthetic Atmosphere
    prompt = """A couple sit on a park bench communicating. The camera maintains a fixed shot 
    of the couple from a respectful distance. The autumn leaves fall gently around them, 
    and their gestures show deep engagement in conversation. The color tone is warm and 
    natural, creating a cozy and intimate atmosphere as the late afternoon sun casts 
    long shadows through the trees."""

    # Generate video from text asynchronously
    response = await client.text_to_video(text=prompt, wait_for_completion=True)
    print(f"Generated video file ID: {response.file_id}")

    # Download the video
    file_info = await client.retrieve_video(file_id=response.file_id, download_path="output_video_async.mp4")
    print(f"Video downloaded to: output_video_async.mp4")


if __name__ == "__main__":
    asyncio.run(main())
