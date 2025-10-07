# main.py or send_x_videos.py
from db import *  # establishes connection

from models import Video
from send_x_videos import send_x_videos

def get_failed_videos():
    """Fetch videos that have failed in all trials."""
    failed_videos = []
    for v in Video.objects(trials__not__size=0):
        if all(t.status == "failed" for t in v.trials):
            failed_videos.append(v)
    return failed_videos


def retry_failed_videos():
    """Retry sending all permanently failed videos."""
    failed_videos = get_failed_videos()
    
    for vid in failed_videos:
        print(vid.video_id, vid.tweet_url)
        
    print(f"🔁 Found {len(failed_videos)} failed videos to retry.")

    for video in failed_videos:
        video_info = {
            "tweet_id": video.video_id,
            "tweet_url": video.tweet_url,
            "username": video.uploader_username,
            "text": video.description,
            "preview": video.preview,
            "tags": [t.name for t in video.tags],
            "video_url": video.tweet_url,  # Replace with actual video URL source if needed
        }

        try:
            print(f"🚀 Retrying: {video.tweet_url}")
            send_x_videos(video_info, mechanism_name="retry_mechanism")
        except Exception as e:
            print(f"❌ Retry failed for {video.tweet_url}: {e}")


if __name__ == "__main__":
    retry_failed_videos()
