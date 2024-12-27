import os
from minimax import Minimax

# Initialize the client
client = Minimax(api_key=os.getenv("MINIMAX_API_KEY"))

# Basic Prompt Formula = Main Subject + Scene + Motion
prompt = """A small stream flows quietly in a valley.
The crystal-clear water gently cascades over smooth rocks,
creating ripples that catch the sunlight."""

# Generate video from text
response = client.text_to_video(text=prompt, wait_for_completion=True)
print(f"Generated video file ID: {response.file_id}")

# Download the video
file_info = client.retrieve_video(file_id=response.file_id, download_path="output_video.mp4")
print(f"Video downloaded to: output_video.mp4")
