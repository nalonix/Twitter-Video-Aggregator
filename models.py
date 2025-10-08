from mongoengine import Document, StringField, BooleanField, FloatField, IntField, ListField, ReferenceField, DateTimeField
from datetime import datetime, timezone

class Tag(Document):
    name = StringField(required=True, unique=True)
    total_videos = IntField(default=0)
    total_views = IntField(default=0)
    total_size_mb = FloatField(default=0.0)
    last_used_at = DateTimeField(default=datetime.now(timezone.utc))

class TrialLog(Document):
    """
    Logs a single attempt to send a video via a mechanism.
    """
    mechanism_name = StringField(required=True, choices=["mechanism_1", "mechanism_2"])
    attempt_number = IntField(default=1)
    status = StringField(choices=["ongoing", "completed", "failed"], default="ongoing")
    error_message = StringField()
    duration_seconds = FloatField(default=0.0)
    telegram_file_id = StringField()           # Stores the Telegram file_id
    channel_message_id = StringField()         # Stores the message_id in the Telegram channel
    created_at = DateTimeField(default=datetime.now(timezone.utc))

class Video(Document):
    """
    One entry per video (unique by tweet_id or tweet_url).
    """
    video_id = StringField(required=True, unique=True)  # Use tweet_id
    uploader_username = StringField(required=True)
    tags = ListField(ReferenceField(Tag))
    duration_seconds = FloatField(default=0)
    size_mb = FloatField(default=0)
    trials = ListField(ReferenceField(TrialLog))
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    completed_at = DateTimeField()
    
    # Tweet-related info
    tweet_url = StringField()
    title = StringField()
    description = StringField()
    preview = StringField()


class LikedVideoDump(Document):
    """
    Temporary storage for liked video data fetched from the X/Twitter API.
    A simple dump to collect all paginated results before processing.
    """
    tweet_id = StringField(required=True, unique=True)
    tweet_url = StringField()
    username = StringField(required=True)
    text = StringField()
    video_url = StringField(required=True)
    preview = StringField()
    grabbed = BooleanField(default=False)
    tags = ListField(StringField()) 
    collected_at = DateTimeField(default=datetime.now(timezone.utc))

    meta = {
        'collection': 'liked_video_dump'
    }