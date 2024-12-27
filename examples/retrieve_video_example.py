from minimax import Minimax

# Initialize the client
client = Minimax()

# The task_id from a previous video generation
task_id = "012345678901234"

# Retrieve and download the video (will automatically wait for task completion)
file_info = client.retrieve_video(task_id=task_id, download_path="retrieved_video.mp4")
print(f"Video downloaded successfully to: retrieved_video.mp4")
print(f"File info: {file_info}")
