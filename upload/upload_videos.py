import time
import winsound

import core.db  # noqa: F401  establishes connection
from core.bot import bot
from core.constants import PRIVATE_CHANNEL_ID, TELEGRAM_CHAT_ID
from upload.failed_uploads_logger import FailedUploadsLogger
from upload.grab_vids import grab_vids
from upload.send_x_videos import send_x_videos


if __name__ == "__main__":
    RUNS = 1

    MAX_RESULTS = None
    BREAK_INTERVAL = 4 * 60  # 4 minutes
    BREAK_DURATION = 30  # 30 seconds

    failed_logger = FailedUploadsLogger()
    total_attempted = 0
    total_success = 0
    total_bot_success = 0
    total_channel_success = 0

    for run in range(RUNS):
        print(f"⚡ Starting run {run + 1}/{RUNS}")
        start_time = time.time()
        run_attempted = 0
        run_success = 0
        run_bot_success = 0
        run_channel_success = 0

        liked_data = grab_vids(max_results=MAX_RESULTS)

        for i, vid in enumerate(liked_data):
            run_attempted += 1
            total_attempted += 1

            try:
                result = send_x_videos(vid, failed_logger=failed_logger)
                if result.get("sent_to_bot"):
                    run_bot_success += 1
                    total_bot_success += 1

                if result.get("sent_to_channel"):
                    run_channel_success += 1
                    total_channel_success += 1

                if result.get("sent_to_bot") and result.get("sent_to_channel"):
                    run_success += 1
                    total_success += 1

                total_processed = len(liked_data)
                progress = ((i + 1) / total_processed * 100) if total_processed else 0.0
                print(
                    f"📈 Progress {progress:.1f}% "
                    f"{i + 1}/{total_processed} | Run {run + 1}/{RUNS}\n"
                )

                time.sleep(2)
            except Exception as e:
                print(f"❌ Failed to send video for tweet {vid.get('id')}\nReason: {e}")

            elapsed = time.time() - start_time
            if elapsed > BREAK_INTERVAL:
                print(f"⏸ 5 minutes reached. Taking a {BREAK_DURATION}s break...")
                time.sleep(BREAK_DURATION)
                start_time = time.time()

        run_bot_rate = (run_bot_success / run_attempted * 100) if run_attempted else 0.0
        run_channel_rate = (run_channel_success / run_attempted * 100) if run_attempted else 0.0
        run_rate = (run_success / run_attempted * 100) if run_attempted else 0.0
        print(
            f"📊 Run {run + 1}/{RUNS} delivery summary: "
            f"bot={run_bot_success}/{run_attempted} ({run_bot_rate:.1f}%) | "
            f"channel={run_channel_success}/{run_attempted} ({run_channel_rate:.1f}%) | "
            f"end-to-end={run_success}/{run_attempted} ({run_rate:.1f}%)"
        )
        print(f"✅ Run {run + 1} complete.\n")

    failed_logger.save()

    overall_bot_rate = (total_bot_success / total_attempted * 100) if total_attempted else 0.0
    overall_channel_rate = (total_channel_success / total_attempted * 100) if total_attempted else 0.0
    overall_rate = (total_success / total_attempted * 100) if total_attempted else 0.0
    print(
        f"📊 Overall delivery summary: "
        f"bot={total_bot_success}/{total_attempted} ({overall_bot_rate:.1f}%) | "
        f"channel={total_channel_success}/{total_attempted} ({overall_channel_rate:.1f}%) | "
        f"end-to-end={total_success}/{total_attempted} ({overall_rate:.1f}%)"
    )

    bot.sendMessage(PRIVATE_CHANNEL_ID, "✅ Run complete.")
    bot.sendMessage(TELEGRAM_CHAT_ID, "✅ Run complete.")
    winsound.Beep(300, 1000)
