import time
from datetime import datetime, timezone

from core.bot import bot
from core.constants import PARSE_MODE, PRIVATE_CHANNEL_ID, TELEGRAM_CHAT_ID
from core.generate_title import generate_title
from upload.video_logger import create_or_get_video, get_or_create_tags, log_trial


def _is_transient_telegram_error(exc: Exception) -> bool:
    message = str(exc).lower()
    transient_markers = (
        "connection aborted",
        "connection reset",
        "connection reset by peer",
        "temporarily unavailable",
        "timed out",
        "try again later",
    )
    return any(marker in message for marker in transient_markers)


def _send_video_to_chat(chat_id: int | str, video_source, caption: str, retries: int = 2):
    """Send the remote video directly to Telegram with a short retry window for transient transport resets."""
    last_exc = None
    is_remote_url = isinstance(video_source, (str, bytes)) and str(video_source).startswith("http")

    for attempt in range(retries + 1):
        try:
            return bot.sendVideo(
                chat_id=chat_id,
                video=video_source,
                caption=caption,
                parse_mode=PARSE_MODE,
            )
        except Exception as exc:
            last_exc = exc
            if is_remote_url and attempt < retries and _is_transient_telegram_error(exc):
                time.sleep(0.5)
                continue
            raise

    raise last_exc


def send_x_videos(
    video_info: dict, mechanism_name: str = "mechanism_1", failed_logger=None
):
    username = video_info.get("username")
    user_display_name = video_info.get("user_display_name", username)
    video_url = video_info.get("video_url")

    if not video_url:
        print(f"⚠️ [BOT] Missing video URL for tweet {video_info.get('id')}")
        return {
            "sent_to_bot": False,
            "sent_to_channel": False,
            "channel_method": None,
            "error_message": "Missing video URL",
        }

    tags = get_or_create_tags(video_info.get("tags", []))
    video = create_or_get_video(video_info, username, tags)
    tweet_url = f"https://x.com/{username}/status/{video_info.get('id')}"

    start_time = time.time()
    error_msg = ""
    result = {
        "sent_to_bot": False,
        "sent_to_channel": False,
        "channel_method": None,
        "main_message_id": None,
        "private_message_id": None,
        "main_file_id": None,
        "error_message": "",
    }

    try:
        caption = (
            f"🎬 *{generate_title(video_info.get('text', ''))}*\n\n"
            f"{video_info.get('text', '')}\n\n"
            f"👤 [{user_display_name}](https://x.com/{username})\n\n"
            f"[View on X]({tweet_url})"
        )

        res_main = _send_video_to_chat(
            chat_id=TELEGRAM_CHAT_ID,
            video_source=video_url,
            caption=caption,
        )
        main_file_id = res_main["video"]["file_id"]
        main_message_id = res_main["message_id"]
        result["sent_to_bot"] = True
        result["main_message_id"] = main_message_id
        result["main_file_id"] = main_file_id
        print(f"✅ [BOT] Video delivered to bot chat for tweet {video_info.get('id')} | message_id={main_message_id}")

        # 2) Forward the bot message to the archive channel first so we do not re-upload the same media.
        try:
            forwarded = bot.forwardMessage(
                chat_id=PRIVATE_CHANNEL_ID,
                from_chat_id=TELEGRAM_CHAT_ID,
                message_id=main_message_id,
            )
            private_message_id = forwarded["message_id"]
            result["sent_to_channel"] = True
            result["channel_method"] = "forwardMessage"
            result["private_message_id"] = private_message_id
            print(f"✅ [CHANNEL] Bot message forwarded to archive channel for tweet {video_info.get('id')} | message_id={private_message_id}")
        except Exception as channel_error:
            channel_error_msg = str(channel_error)
            print(
                f"⚠️ [CHANNEL] ForwardMessage failed for tweet {video_info.get('id')}. "
                f"Trying file_id fallback. Reason: {channel_error_msg}"
            )

            try:
                res_private = bot.sendVideo(
                    chat_id=PRIVATE_CHANNEL_ID,
                    video=main_file_id,
                    caption=caption,
                    parse_mode=PARSE_MODE,
                )
                private_message_id = res_private["message_id"]
                result["sent_to_channel"] = True
                result["channel_method"] = "sendVideo(file_id)"
                result["private_message_id"] = private_message_id
                print(f"✅ [CHANNEL] Video delivered to archive channel for tweet {video_info.get('id')} | message_id={private_message_id}")
            except Exception as file_id_error:
                fallback_msg = str(file_id_error)
                print(
                    f"❌ [CHANNEL] File-id fallback also failed for tweet {video_info.get('id')}. "
                    f"Reason: {fallback_msg}"
                )
                raise RuntimeError(
                    f"Bot delivered successfully, but channel delivery failed: "
                    f"forward => {channel_error_msg}; fallback file_id => {fallback_msg}"
                )

        duration = time.time() - start_time

        video.size_mb = res_main["video"]["file_size"] / (1024 * 1024)
        video.duration_seconds = res_main["video"].get("duration", 0)
        video.completed_at = datetime.now(timezone.utc)
        video.message_id_main = str(main_message_id)
        video.message_id_private = str(private_message_id)

        video.tweet_type = video_info.get("tweet_type")
        video.source = str(video_info.get("source") or "")
        video.retweet_count = int(video_info.get("retweet_count", 0))
        video.favorite_count = int(video_info.get("favorite_count", 0))
        video.view_count = int(video_info.get("view_count", 0))
        video.thumbnail_url = video_info.get("thumbnail_url")
        video.conversation_id_str = video_info.get("conversation_id_str")
        video.keywords = video_info.get("keywords", [])
        video.fake_timestamp = video_info.get("fake_timestamp")
        video.fake_date = video_info.get("fake_date")
        video.video_url = video_info.get("video_url")
        video.media_urls = video_info.get("media_urls", [])
        video.video_duration = video_info.get("video_duration", 0)
        video.uploader_display_name = video_info.get("user_display_name", username)

        video.save()

        log_trial(
            video,
            mechanism_name=mechanism_name,
            status="completed",
            duration=duration,
            telegram_file_id=main_file_id,
            channel_message_id=str(private_message_id),
            bot_sent=True,
            channel_sent=True,
            channel_delivery_method=result["channel_method"],
        )

        print(f"✅ Video sent successfully: {video.video_id}")
        return result

    except Exception as e:
        error_msg = str(e)
        duration = time.time() - start_time

        if result.get("sent_to_bot") and result.get("main_message_id"):
            video.message_id_main = str(result["main_message_id"])
            video.message_id_private = str(result.get("private_message_id") or "")
            video.size_mb = (result.get("main_file_size") or 0) / (1024 * 1024)
            video.duration_seconds = result.get("main_duration_seconds") or 0
            video.completed_at = datetime.now(timezone.utc)
            video.video_url = video_info.get("video_url")
            video.uploader_display_name = video_info.get("user_display_name", username)
            video.save()

        log_trial(
            video,
            mechanism_name=mechanism_name,
            status="failed",
            duration=duration,
            error_message=error_msg,
            bot_sent=result.get("sent_to_bot", False),
            channel_sent=result.get("sent_to_channel", False),
            channel_delivery_method=result.get("channel_method", ""),
        )

        print(f"❌ Failed to send video: {video_info.get('id')}\nReason: {error_msg}")

        if failed_logger:
            failed_logger.log_failure(video_info)

        return {
            "sent_to_bot": result.get("sent_to_bot", False),
            "sent_to_channel": False,
            "channel_method": None,
            "main_message_id": result.get("main_message_id"),
            "private_message_id": None,
            "main_file_id": result.get("main_file_id"),
            "error_message": error_msg,
        }
