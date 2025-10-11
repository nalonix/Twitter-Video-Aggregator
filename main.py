import json
from constants import PRIVATE_CHANNEL_ID, TELEGRAM_CHAT_ID
from db import *  # establishes connection
import time
from scrapped.grab_vids import grab_vids
from send_x_videos import send_x_videos

from bot import bot

if __name__ == "__main__":
    RUNS = 4
    
    MAX_RESULTS = 100
    BREAK_INTERVAL = 4 * 60  # 3 minutes
    BREAK_DURATION = 30      # 30 seconds

    for run in range(RUNS):
        print(f"⚡ Starting run {run + 1}/{RUNS}")
        start_time = time.time()

        liked_data = grab_vids(max_results=MAX_RESULTS)

        for i, vid in enumerate(liked_data):
            try:
                send_x_videos(vid)
                
                print(f"📈 Progress {((run * MAX_RESULTS + (i + 1)) / (MAX_RESULTS * RUNS)) * 100:.1f}% " f"{run * MAX_RESULTS + (i + 1)}/{MAX_RESULTS * RUNS} | Run {run + 1}/{RUNS}\n")

                time.sleep(2)  # small delay between sending videos
            except Exception as e:
                print(f"❌ Failed to send video for tweet {vid.get('id')}\nReason: {e}")

            # Check elapsed time to decide on break
            elapsed = time.time() - start_time
            if elapsed > BREAK_INTERVAL:
                print(f"⏸ 5 minutes reached. Taking a {BREAK_DURATION}s break...")
                time.sleep(BREAK_DURATION)
                start_time = time.time()  # reset timer after break

        print(f"✅ Run {run + 1} complete.\n")
        
    bot.sendMessage(PRIVATE_CHANNEL_ID, "✅ Run complete.")
    bot.sendMessage(TELEGRAM_CHAT_ID, "✅ Run complete.")

