import os
from minimax import Minimax

# Initialize the client with your API key
client = Minimax(api_key=os.getenv("MINIMAX_API_KEY"))

# Basic Prompt Formula = Main Subject + Scene + Motion
prompt = """A golden retriever puppy plays in a sunny garden. 
The puppy joyfully chases a red ball through blooming flowers, 
while butterflies flutter around in the background."""

# Create the video
output_path = client.create_video(text=prompt)
print(f"Video generated and downloaded to: {output_path}")
