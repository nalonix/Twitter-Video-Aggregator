# video_logger.py
from datetime import datetime, timezone
from typing import List, Dict
from core.generate_title import generate_title
from core.models import Video, Tag, TrialLog


# ----------------------
# Tag Helpers
# ----------------------
def get_or_create_tag(tag_name: str) -> Tag:
    """Fetch an existing Tag by name or create a new one."""
    tag = Tag.objects(name=tag_name).first()
    if tag:
        # Update usage stats
        tag.last_used_at = datetime.now(timezone.utc)
        tag.save()
        return tag

    return Tag(name=tag_name).save()


def get_or_create_tags(tag_names: List[str]) -> List[Tag]:
    """Batch create or fetch tags."""
    return [get_or_create_tag(name.strip()) for name in tag_names if name.strip()]


# ----------------------
# Video & Trial Helpers
# ----------------------
def create_or_get_video(video_info: Dict, username: str, tags: List[Tag]) -> Video:
    """
    Return existing video by id, or create a new one.
    Updates metadata and tags if already exists.
    """
    video_id = str(video_info.get("id") )
    if not video_id:
        raise ValueError("video_info must include tweet_id or video_id")

    video = Video.objects(video_id=video_id).first()

    if video:
        # Update tags if any new ones
        existing_tag_ids = {str(t.id) for t in video.tags}
        for tag in tags:
            if str(tag.id) not in existing_tag_ids:
                video.tags.append(tag)
        # Keep video_url populated so failed uploads can be retried from the DB
        if not video.video_url and video_info.get("video_url"):
            video.video_url = video_info.get("video_url")
        video.save()
        return video

    # Create new entry
    # video_url and uploader_display_name are stored up-front (not only on success)
    # so retry_failed_uploads.py can resend failures without a backfill.
    text_content = video_info.get("text", "")
    new_video = Video(
        video_id=video_id,
        uploader_username=username,
        uploader_display_name=video_info.get("user_display_name") or username,
        tweet_url=video_info.get("tweet_url") or f"https://x.com/{username}/status/{video_id}",
        title=generate_title(text_content),
        description=text_content,
        text=text_content,
        source=str(video_info.get("source") or ""),
        tags=tags,
        video_url=video_info.get("video_url"),
        media_urls=video_info.get("media_urls", []),
        thumbnail_url=video_info.get("thumbnail_url", ""),
        tweet_type=video_info.get("tweet_type", ""),
        conversation_id_str=video_info.get("conversation_id_str", ""),
        retweet_count=video_info.get("retweet_count", 0),
        favorite_count=video_info.get("favorite_count", 0),
        view_count=video_info.get("view_count", 0),
        created_at=datetime.now(timezone.utc)
    ).save()

    return new_video


def log_trial(
    video: Video,
    mechanism_name: str,
    status: str,
    duration: float,
    error_message: str = "",
    telegram_file_id: str = "",
    channel_message_id: str = "",
    bot_sent: bool = False,
    channel_sent: bool = False,
    channel_delivery_method: str = ""
) -> TrialLog:
    """Log a single trial attempt for a video."""
    trial = TrialLog(
        mechanism_name=mechanism_name,
        attempt_number=len(video.trials) + 1,
        status=status,
        duration_seconds=duration,
        error_message=error_message,
        bot_sent=bot_sent,
        channel_sent=channel_sent,
        channel_delivery_method=channel_delivery_method,
        telegram_file_id=telegram_file_id,
        channel_message_id=channel_message_id,
    ).save()

    video.trials.append(trial)
    video.save()
    return trial
