import asyncio
from minimax import AsyncMinimax


async def main():
    # Initialize the async client
    client = AsyncMinimax()

    # The task_id from a previous video generation
    task_id = "012345678901234"

    # Retrieve and download the video (will automatically wait for task completion)
    file_info = await client.retrieve_video(task_id=task_id, download_path="retrieved_video_async.mp4")
    print(f"Video downloaded successfully to: retrieved_video_async.mp4")
    print(f"File info: {file_info}")


if __name__ == "__main__":
    asyncio.run(main())
