from mongoengine import (
    Document, StringField, BooleanField, FloatField, IntField, 
    ListField, ReferenceField, DateTimeField
)
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
    Stores both scraped and liked videos.
    """
    video_id = StringField(required=True, unique=True)  # tweet_id
    uploader_username = StringField(required=True)
    uploader_display_name = StringField()
    
    # Relations
    tags = ListField(ReferenceField(Tag))
    trials = ListField(ReferenceField(TrialLog))

    # Video info
    duration_seconds = FloatField(default=0)
    video_duration = FloatField(default=0)  # kept for clarity from liked dump
    size_mb = FloatField(default=0)
    video_url = StringField()
    media_urls = ListField(StringField())
    thumbnail_url = StringField()
    completed_at = DateTimeField()
    
    # Tweet info
    tweet_type = StringField()
    tweet_url = StringField()
    title = StringField()
    description = StringField()
    text = StringField()
    source = StringField()
    conversation_id_str = FloatField()
    retweet_count = IntField(default=0)
    favorite_count = IntField(default=0)
    view_count = IntField(default=0)

    # Analysis/metadata
    keywords = ListField(StringField())
    fake_timestamp = IntField()
    fake_date = StringField()
        
    created_at = DateTimeField(default=datetime.now(timezone.utc))
