import time
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from grab_vids import grab_vids
from models import LikedVideoDump



def fetch_all_liked_videos() -> List['LikedVideoDump']:
    """
    Triggers the fetching of all liked videos from the X/Twitter API 
    by following the pagination token and saves them into the LikedVideoDump collection.

    NOTE: This function assumes that 'get_liked_videos' is available in the scope 
    (either imported or defined in the same file).
    """
    all_saved_videos: List['LikedVideoDump'] = []
    next_token: Optional[str] = None
    page_count = 1
    
    print("🚀 Starting full fetch of all liked videos...")

    while True:
        print(f"\n--- Fetching Page {page_count} (Token: {next_token}) ---")
        
        # 1. Functional Call to get_liked_videos
        result = grab_vids(pagination_token=next_token)
        videos_data = result["videos"]
        current_next_token = result["next_token"]
        
        if not videos_data and not current_next_token:
            print("🛑 No videos or no more pages found. Stopping.")
            break
        
        # If videos_data is empty but current_next_token is present, it might be a rate limit
        # recovery scenario or an API quirk; we continue to the next page if possible.
        if not videos_data:
             print("⚠️ No videos found on this page. Checking for next token...")

        # 2. Insert/Update Data into the Model
        saved_on_page = 0
        for video_data in videos_data:
            try:
                # Use modify(upsert=True) to insert or update based on 'tweet_id'
                dump_entry = LikedVideoDump.objects(tweet_id=video_data["tweet_id"]).modify(
                    upsert=True,
                    new=True, 
                    set__tweet_url=video_data["tweet_url"],
                    set__username=video_data["username"],
                    set__text=video_data["text"],
                    set__video_url=video_data["video_url"],
                    set__preview=video_data.get("preview"),
                    set__tags=video_data.get("tags", []),
                    set__collected_at=datetime.now(timezone.utc)
                    # 'grabbed' is only updated when we process the video later
                )
                all_saved_videos.append(dump_entry)
                saved_on_page += 1
            except Exception as e:
                print(f"⚠️ Could not save video with tweet_id {video_data.get('tweet_id')}: {e}")
                
        print(f"💾 Saved/Updated {saved_on_page} videos from Page {page_count}.")
        
        # 3. Handle Pagination
        if not current_next_token:
            print("✅ Pagination complete. No next token found.")
            break
            
        # Avoid getting stuck in a loop if the token doesn't advance (shouldn't happen, but safe)
        if current_next_token == next_token:
             print("⚠️ Next token is the same as the current token. Stopping to prevent infinite loop.")
             break
            
        next_token = current_next_token
        page_count += 1
        
        # Wait before the next API call (to be gentle and respect general rate limits)
        time.sleep(2) 
        
    print(f"\n✨ Total of {len(all_saved_videos)} unique video entries processed and saved.")
    return all_saved_videos