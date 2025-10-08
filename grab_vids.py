import time
from typing import Dict, Any, Optional
import requests
from requests_oauthlib import OAuth1
from extract_video_urls import extract_video_urls
from constants import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_USER_ID,
)


def grab_vids(max_results: int = 40, pagination_token: Optional[str] = None) -> Dict[str, Any]:
    base_url = f"https://api.x.com/2/users/{TWITTER_USER_ID}/liked_tweets"
    params = {
        "expansions": "attachments.media_keys,author_id",
        "media.fields": "media_key,type,variants,preview_image_url,duration_ms,height,width",
        "tweet.fields": "id,text,attachments,created_at,entities",
        "user.fields": "id,username,name,profile_image_url",
        "max_results": max_results,
    }
    if pagination_token:
        params["pagination_token"] = pagination_token

    auth = OAuth1(
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
    )

    try:
        print("📡 Fetching liked tweets...")
        res = requests.get(base_url, params=params, auth=auth)

        if res.status_code == 429:
            reset_time = int(res.headers.get("x-rate-limit-reset", time.time() + 60))
            
            wait_sec = max(reset_time - int(time.time()), 60) 
            
            print(f"⚠️ Rate limit reached. Sleeping for {wait_sec} seconds.")
            time.sleep(wait_sec)
            
            return grab_vids(max_results, pagination_token)

        res.raise_for_status()
        data = res.json()
        

        videos = extract_video_urls(data)
        next_token = data.get("meta", {}).get("next_token")
        print(f"🎞️ Found {len(videos)} video tweets.")
        print("🌄 Videos: ", videos)
        return {"videos": videos, "next_token": next_token}

    except Exception as e:
        print(f"❌ Error fetching liked videos: {e}")
        return {"videos": [], "next_token": None}


