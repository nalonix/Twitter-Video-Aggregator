# main.py or send_x_videos.py
from db import *  # establishes connection

import time
from get_liked_videos import get_liked_videos
from send_x_videos import send_x_videos

#temp
from liked_vids import liked_vid


if __name__ == "__main__":
    liked_data = get_liked_videos(max_results=30)
    print("👺 Found liked videos: ", liked_data)

    for vid in liked_data.get("videos", []):
        try:
            send_x_videos(vid)
            time.sleep(3)
        except Exception as e:
            print(f"❌ Failed to send video for tweet {vid.get('tweet_id')}\nReason: {e}")
