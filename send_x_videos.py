from datetime import datetime, timezone
import json
from video_logger import get_or_create_tags, create_or_get_video, log_trial
import time
import telepot
from generate_title import generate_title
from constants import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRIVATE_CHANNEL_ID, PARSE_MODE


bot = telepot.Bot(TELEGRAM_TOKEN)


def send_x_videos(video_info: dict, mechanism_name: str = "mechanism_1"):
    username = video_info.get("username")
    video_url = video_info.get("video_url")

    # Handle missing video URL early
    if not video_url:
        print(f"⚠️ Missing video URL for tweet {video_info.get('id')}")
        return

    # Prepare tags
    tags = get_or_create_tags(video_info.get("tags", []))
    video = create_or_get_video(video_info, username, tags)
    tweet_url = f"https://x.com/{username}/status/{video_info.get('id')}"

    start_time = time.time()
    error_msg = ""

    try:
        # -------------------------------
        # Telegram caption setup
        # -------------------------------
        caption = (
            f"🎬 *{generate_title(video_info.get('text', ''))}*\n\n"
            f"{video_info.get('text', '')}\n\n"
            f"👤 [{username}](https://x.com/{username})\n\n"
            f"[View on X]({tweet_url})"
        )

        # -------------------------------
        # Send to Telegram Bot
        # -------------------------------
        res_main = bot.sendVideo(
            chat_id=TELEGRAM_CHAT_ID,
            video=video_url,
            caption=caption,
            parse_mode=PARSE_MODE,
        )

        main_file_id = res_main["video"]["file_id"]
        main_message_id = res_main["message_id"]

        # -------------------------------
        # Forward to private archive channel
        # -------------------------------
        res_private = bot.sendVideo(
            chat_id=PRIVATE_CHANNEL_ID,
            video=main_file_id,
            caption=caption,
            parse_mode=PARSE_MODE,
        )
        private_message_id = res_private["message_id"]

        # -------------------------------
        # Update DB metadata
        # -------------------------------
        duration = time.time() - start_time

        video.size_mb = res_main["video"]["file_size"] / (1024 * 1024)
        video.duration_seconds = res_main["video"].get("duration", 0)
        video.completed_at = datetime.now(timezone.utc)

        # Populate new attributes if provided
        video.tweet_type = video_info.get("tweet_type")
        video.source = video_info.get("source")
        video.retweet_count = int(video_info.get("retweet_count", 0))
        video.favorite_count = int(video_info.get("favorite_count", 0))
        video.view_count = int(video_info.get("view_count", 0))
        video.thumbnail_url = video_info.get("thumbnail_url")
        video.conversation_id_str = video_info.get("conversation_id_str")
        video.keywords = video_info.get("keywords", [])
        video.fake_timestamp = video_info.get("fake_timestamp")
        video.fake_date = video_info.get("fake_date")
        video.media_urls = video_info.get("media_urls", [])
        video.video_duration = video_info.get("video_duration", 0)

        video.save()

        # -------------------------------
        # Log success
        # -------------------------------
        log_trial(
            video,
            mechanism_name=mechanism_name,
            status="completed",
            duration=duration,
            telegram_file_id=main_file_id,
            channel_message_id=str(private_message_id)
        )

        print(f"✅ Video sent successfully: {video.video_id}")

    except Exception as e:
        error_msg = str(e)
        duration = time.time() - start_time

        # Log failure trial
        log_trial(
            video,
            mechanism_name=mechanism_name,
            status="failed",
            duration=duration,
            error_message=error_msg
        )

        print(f"❌ Failed to send video: {video_info.get('id')}\nReason: {error_msg}")
