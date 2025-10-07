from typing import List, Dict, Any
import re

def extract_video_urls(response_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    media_map = {m["media_key"]: m for m in response_json.get("includes", {}).get("media", [])}
    user_map = {u["id"]: u["username"] for u in response_json.get("includes", {}).get("users", [])}
    results: List[Dict[str, Any]] = []

    for tweet in response_json.get("data", []):
        media_keys = tweet.get("attachments", {}).get("media_keys", [])
        text = tweet.get("text", "")
        tweet_id = tweet.get("id", "")
        author_id = tweet.get("author_id")
        username = user_map.get(author_id, "unknown")

        tweet_url = f"https://x.com/{username}/status/{tweet_id}" if username != "unknown" else f"https://x.com/i/web/status/{tweet_id}"

        # Extract hashtags from entities if available
        entities = tweet.get("entities", {})
        hashtags = [h["tag"] for h in entities.get("hashtags", [])] if "hashtags" in entities else []

        # Fallback: parse hashtags from text using regex if entities missing
        if not hashtags:
            hashtags = re.findall(r"#(\w+)", text)

        for key in media_keys:
            media = media_map.get(key)
            if not media or media.get("type") != "video":
                continue

            variants = [
                v for v in media.get("variants", [])
                if v.get("content_type") == "video/mp4" and "bit_rate" in v
            ]
            if not variants:
                continue

            best_variant = max(variants, key=lambda v: v["bit_rate"])
            results.append({
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "username": username,
                "text": text,
                "video_url": best_variant["url"],
                "preview": media.get("preview_image_url"),
                "tags": hashtags 
            })

    return results
