# X Likes Downloader

Small utility to fetch liked tweets that contain videos and forward them to a Telegram chat/channel while logging attempts to MongoDB.

## Quick overview
- Fetch likes from X (Twitter) using OAuth: see [`get_liked_videos`](get_liked_videos.py) and [get_liked_videos.py](get_liked_videos.py).  
- Extract video URLs from API responses: see [`extract_video_urls`](extract_video_urls.py) and [extract_video_urls.py](extract_video_urls.py).  
- Send videos to Telegram and forward to a private channel: see [`send_x_videos`](send_x_videos.py) and [send_x_videos.py](send_x_videos.py).  
- Generate short titles/summaries: see [`generate_title`](generate_title.py) and [generate_title.py](generate_title.py).  
- Log video/trial data into MongoDB models: see [`Video`], [`Tag`], [`TrialLog`] in [models.py](models.py) and logging helpers in [video_logger.py](video_logger.py) (e.g. [`log_success`](video_logger.py), [`log_failure`](video_logger.py), [`log_trial`](video_logger.py)).  
- DB connection is initialized in [db.py](db.py). Example liked-data for testing is in [liked_vids.py](liked_vids.py).

## Requirements
- Python 3.10+ (use your project's venv)
- Dependencies: requests, requests-oauthlib, python-dotenv, mongoengine, telepot, sumy (see imports in files)

## Setup
1. Copy [env.example](env.example) -> `.env` and fill credentials (Telegram token, MongoDB URI, Twitter API keys).
2. Remove secrets from [constants.py](constants.py) and prefer environment variables. `.gitignore` already excludes `.env` and `constants*`.
3. Install deps:
```sh
pip install -r requirements.txt