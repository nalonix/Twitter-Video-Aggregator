import json
from db import *  # establishes connection

import time
from scrapped.grab_vids import grab_vids
from send_x_videos import send_x_videos


if __name__ == "__main__":
    liked_data = grab_vids(max_results=3)

    for vid in liked_data:
        try:
            send_x_videos(vid)
            time.sleep(3)
        except Exception as e:
            print(f"❌ Failed to send video for tweet {vid.get('id')}\nReason: {e}")

