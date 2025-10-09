# video_logger.py
from datetime import datetime, timezone
from typing import List, Dict
from generate_title import generate_title
from models import Video, Tag, TrialLog


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
        video.save()
        return video

    # Create new entry
    text_content = video_info.get("text", "")
    new_video = Video(
        video_id=video_id,
        uploader_username=username,
        uploader_display_name=video_info.get("uploader_display_name", ""),
        tweet_url=video_info.get("tweet_url"),
        title=generate_title(text_content),
        description=text_content,
        text=text_content,
        source=video_info.get("source", "unknown"),
        tags=tags,
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
    channel_message_id: str = ""
) -> TrialLog:
    """Log a single trial attempt for a video."""
    trial = TrialLog(
        mechanism_name=mechanism_name,
        attempt_number=len(video.trials) + 1,
        status=status,
        duration_seconds=duration,
        error_message=error_message,
        telegram_file_id=telegram_file_id,
        channel_message_id=channel_message_id,
    ).save()

    video.trials.append(trial)
    video.save()
    return trial


# ----------------------
# High-Level Logging
# ----------------------
def log_success(
    video_info: Dict,
    username: str,
    duration: float,
    size_mb: float,
    telegram_file_id: str = "",
    channel_message_id: str = ""
):
    """Record a successful download/upload attempt."""
    tags = get_or_create_tags(video_info.get("tags", []))
    video = create_or_get_video(video_info, username, tags)

    # Create trial
    trial = log_trial(
        video,
        mechanism_name="mechanism_1",
        status="completed",
        duration=duration,
        telegram_file_id=telegram_file_id,
        channel_message_id=channel_message_id
    )

    # Update video metadata
    video.duration_seconds = duration
    video.size_mb = size_mb
    video.completed_at = datetime.now(timezone.utc)
    video.save()

    # Update tag usage stats
    for tag in tags:
        tag.total_videos += 1
        tag.total_size_mb += size_mb
        tag.total_views += video.view_count or 0
        tag.last_used_at = datetime.now(timezone.utc)
        tag.save()

    print(f"✅ [LOGGED SUCCESS] {video_info.get('tweet_url')} | Trial #{trial.attempt_number}")


def log_failure(
    video_info: Dict,
    username: str,
    error: str,
    duration: float = 0.0,
    telegram_file_id: str = "",
    channel_message_id: str = ""
):
    """Record a failed attempt."""
    tags = get_or_create_tags(video_info.get("tags", []))
    video = create_or_get_video(video_info, username, tags)

    trial = log_trial(
        video,
        mechanism_name="mechanism_1",
        status="failed",
        duration=duration,
        error_message=error,
        telegram_file_id=telegram_file_id,
        channel_message_id=channel_message_id
    )

    print(f"⚠️ [LOGGED FAILURE] {video_info.get('tweet_url')} | Trial #{trial.attempt_number} | Error: {error}")
