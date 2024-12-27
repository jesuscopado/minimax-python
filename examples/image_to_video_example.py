import os
from minimax import Minimax

# Initialize the client
client = Minimax(api_key=os.getenv("MINIMAX_API_KEY"))

# Basic I2V Prompt Formula = Main Subject in first frame + Motion/Change
prompt = """A blue furry creature in the scene is constantly stirring a 
steaming pot of soup. Then, the blue creature blows on the pot, causing 
the soup in the bowl in front of it to freeze into a block of ice."""

# Generate video from image
image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets/furry_creature.jpeg")
response = client.image_to_video(image=image_path, text=prompt, wait_for_completion=True)
print(f"Generated video file ID: {response.file_id}")

# Download the video
file_info = client.retrieve_video(file_id=response.file_id, download_path="output_video.mp4")
print(f"Video downloaded to: output_video.mp4")
