import os
import asyncio
from minimax import AsyncMinimax


async def main():
    # Initialize the async client
    client = AsyncMinimax(api_key=os.getenv("MINIMAX_API_KEY"))

    # Precise Prompt Formula = Main Subject + Scene + Motion + Camera Movement + Aesthetic Atmosphere
    prompt = """In a modern glass-walled office at sunset, a businesswoman stands by the window.
    The camera slowly tracks forward from the office entrance, moving past modern furniture,
    until it reaches her silhouette. As she turns to face the camera, golden sunlight
    streams through the window, creating a warm, professional atmosphere with lens flares
    and soft shadows. The cityscape visible through the window shows buildings with
    twinkling lights coming alive as day turns to dusk."""

    # Create the video asynchronously
    output_path = await client.create_video(text=prompt)
    print(f"Video generated and downloaded to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
