from datetime import datetime, timezone
from video_logger import get_or_create_tags, create_or_get_video, log_trial
import time
import telepot
from generate_title import generate_title
from constants import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRIVATE_CHANNEL_ID, PARSE_MODE

bot = telepot.Bot(TELEGRAM_TOKEN)

def send_x_videos(video_info: dict, mechanism_name: str = "mechanism_1"):
    username = video_info.get("username")
    video_url = video_info.get("video_url")
    tags = get_or_create_tags(video_info.get("tags", []))
    video = create_or_get_video(video_info, username, tags)
    
    start_time = time.time()
    error_msg = ""

    try:
        caption = (
            f"🎬 *{generate_title(video_info.get('text', ''))}*\n\n"
            f"{video_info.get('text')}\n\n"
            f"👤 [{username}](https://x.com/{username})\n\n"
            f"[View on X]({video.tweet_url})"
        )

        # Send to main Telegram chat
        res_main = bot.sendVideo(
            chat_id=TELEGRAM_CHAT_ID,
            video=video_url,
            caption=caption,
            parse_mode=PARSE_MODE,
        )
        main_file_id = res_main["video"]["file_id"]
        main_message_id = res_main["message_id"]

        # Forward to private channel
        res_private = bot.sendVideo(
            chat_id=PRIVATE_CHANNEL_ID,
            video=main_file_id,
            caption=caption,
            parse_mode=PARSE_MODE,
        )
        private_message_id = res_private["message_id"]

        duration = time.time() - start_time

        # Update Video metadata
        video.size_mb = res_main["video"]["file_size"] / (1024 * 1024)
        video.duration_seconds = res_main["video"].get("duration", 0)
        video.completed_at = datetime.now(timezone.utc)
        video.save()

        # Log successful trial with Telegram IDs
        log_trial(
            video,
            mechanism_name,
            status="completed",
            duration=duration,
            telegram_file_id=main_file_id,
            channel_message_id=str(private_message_id)
        )

        print(f"✅ Video sent successfully: {video.video_id}")

    except Exception as e:
        error_msg = str(e)
        duration = time.time() - start_time

        # Log failed trial
        log_trial(
            video,
            mechanism_name,
            status="failed",
            duration=duration,
            error_message=error_msg
        )

        print(f"❌ Failed to send video: {video.tweet_url}\nReason: {error_msg}")
