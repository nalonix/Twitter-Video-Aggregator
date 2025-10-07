# video_logger.py
from datetime import datetime, timezone
from typing import List, Dict
from generate_title import generate_title
from models import Video, Tag, TrialLog

# ----------------------
# Tag Helpers
# ----------------------
def get_or_create_tag(tag_name: str) -> Tag:
    tag = Tag.objects(name=tag_name).first()
    if tag:
        return tag
    return Tag(name=tag_name).save()

def get_or_create_tags(tag_names: List[str]) -> List[Tag]:
    return [get_or_create_tag(name) for name in tag_names]

# ----------------------
# Video & Trial Logging
# ----------------------
def create_or_get_video(video_info: Dict, username: str, tags: List[Tag]) -> Video:
    """Return existing video by tweet_id, or create a new one."""
    video = Video.objects(video_id=video_info.get("tweet_id")).first()
    if not video:
        text_content = video_info.get("text", "")
        video = Video(
            video_id=video_info.get("tweet_id"),
            uploader_username=username,
            tags=tags,
            duration_seconds=0,
            size_mb=0,
            tweet_url=video_info.get("tweet_url"),
            title=generate_title(text_content),
            description=text_content,
            preview=video_info.get("preview"),
            trials=[],
        ).save()
    return video


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
    tags = get_or_create_tags(video_info.get("tags", []))
    video = create_or_get_video(video_info, username, tags)

    trial = log_trial(
        video,
        mechanism_name="mechanism_1",
        status="completed",
        duration=duration,
        telegram_file_id=telegram_file_id,
        channel_message_id=channel_message_id
    )

    # Update video metadata (size/duration)
    video.duration_seconds = duration
    video.size_mb = size_mb
    video.save()

    print(f"✅ [LOGGED SUCCESS] {video_info.get('tweet_url')} | Trial #{trial.attempt_number}")


def log_failure(
    video_info: Dict,
    username: str,
    error: str,
    duration: float = 0.0,
    telegram_file_id: str = "",
    channel_message_id: str = ""
):
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
