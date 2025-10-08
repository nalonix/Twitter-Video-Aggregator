from db import *  # establishes connection

import time
from get_liked_videos import get_liked_videos
from scrapped.grab_vids import grab_vids
from send_x_videos import send_x_videos


if __name__ == "__main__":
    liked_data = grab_vids(max_results=5)
    print("👺 Found liked videos: ", liked_data)
        
    

    # for vid in liked_data.get("videos", []):
    #     try:
    #         send_x_videos(vid)
    #         time.sleep(3)
    #     except Exception as e:
    #         print(f"❌ Failed to send video for tweet {vid.get('tweet_id')}\nReason: {e}")
