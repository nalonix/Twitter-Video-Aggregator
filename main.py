import json
from db import *  # establishes connection
import time
from scrapped.grab_vids import grab_vids
from send_x_videos import send_x_videos

if __name__ == "__main__":
    RUNS = 4
    MAX_RESULTS = 3
    BREAK_INTERVAL = 5 * 60  # 5 minutes
    BREAK_DURATION = 30      # 30 seconds

    for run in range(RUNS):
        print(f"⚡ Starting run {run + 1}/{RUNS}")
        start_time = time.time()

        liked_data = grab_vids(max_results=MAX_RESULTS)

        for vid in liked_data:
            try:
                send_x_videos(vid)
                time.sleep(3)  # small delay between sending videos
            except Exception as e:
                print(f"❌ Failed to send video for tweet {vid.get('id')}\nReason: {e}")

            # Check elapsed time to decide on break
            elapsed = time.time() - start_time
            if elapsed > BREAK_INTERVAL:
                print(f"⏸ 5 minutes reached. Taking a {BREAK_DURATION}s break...")
                time.sleep(BREAK_DURATION)
                start_time = time.time()  # reset timer after break

        print(f"✅ Run {run + 1} complete.\n")

