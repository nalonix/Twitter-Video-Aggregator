import csv
from datetime import datetime
from pathlib import Path

FAILED_DIR = Path(__file__).resolve().parent.parent / "failed_uploads"


class FailedUploadsLogger:
    """
    Tracks failed uploads during a single upload session and writes them to a
    timestamped CSV file.

    Each row contains:
      - user_display_name
      - description (tweet text)
      - tweet_id
      - post_link (View on X style link)
    """

    def __init__(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        FAILED_DIR.mkdir(exist_ok=True)
        self.csv_path = FAILED_DIR / f"failed_uploads_{timestamp}.csv"
        self.failures = []

    def log_failure(self, video_info: dict):
        """Record a failed upload entry from the video_info dict."""
        username = video_info.get("username", "")
        user_display_name = video_info.get("user_display_name", username)
        description = video_info.get("text", "")
        tweet_id = video_info.get("id", "")
        post_link = f"https://x.com/{username}/status/{tweet_id}"

        self.failures.append({
            "user_display_name": user_display_name,
            "description": description,
            "tweet_id": tweet_id,
            "post_link": post_link,
        })

    def save(self):
        """Write all collected failures to the CSV file."""
        if not self.failures:
            print("✅ No failed uploads this session.")
            return

        fieldnames = ["user_display_name", "description", "tweet_id", "post_link"]

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.failures)

        print(f"📄 {len(self.failures)} failed upload(s) saved to {self.csv_path}")
