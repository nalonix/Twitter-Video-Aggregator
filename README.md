# X Likes Downloader

Takes an export of liked X posts that contain videos, cleans it, uploads the videos to a Telegram bot chat and archive channel, and logs every video and attempt to MongoDB.

**How to run it: see [WORKFLOW.md](WORKFLOW.md).**

## Setup

1. Python 3.10+ with a venv:
   ```sh
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `core/constants.example.py` to `core/constants.py` and fill in the Telegram token, chat/channel ids and MongoDB URI. `core/constants.py` is gitignored.
3. Put your likes export at `scrapped/New Data.csv` and run `python run_full_workflow.py`.
