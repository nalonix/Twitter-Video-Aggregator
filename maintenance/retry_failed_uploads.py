"""
retry_failed_uploads.py
───────────────────────
Reads failed_uploads/failed_uploads_*.csv, looks up each video in MongoDB by
tweet ID (extracted from the post_link URL), downloads the video and re-uploads
it to Telegram (mechanism_2), and writes any second-attempt failures to
failed_uploads/second_fail_[timestamp].csv.

Videos whose latest trial is already "completed" are skipped, so re-running
over old CSVs never double-posts.

Usage (from the project root):
    python -m maintenance.retry_failed_uploads                 # every failed_uploads_*.csv
    python -m maintenance.retry_failed_uploads failed_uploads/failed_uploads_X.csv
"""

import csv
import glob
import os
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import telepot

import core.db  # noqa: F401  establishes connection
from core.constants import PARSE_MODE, PRIVATE_CHANNEL_ID, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN
from core.models import TrialLog, Video

# ── CONFIG ────────────────────────────────────────────────────────────────────
FAILED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "failed_uploads")
DELAY_BETWEEN = 2  # seconds between each send
# ─────────────────────────────────────────────────────────────────────────────

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"


def c(t, *x):
    return "".join(x) + str(t) + RESET


def ts():
    return c(f"[{datetime.now().strftime('%H:%M:%S')}]", DIM)


def log_info(m):
    print(f"{ts()} {c('INFO', BLUE, BOLD)}  {m}")


def log_ok(m):
    print(f"{ts()} {c('OK  ', GREEN, BOLD)}  {m}")


def log_warn(m):
    print(f"{ts()} {c('WARN', YELLOW, BOLD)}  {m}")


def log_err(m):
    print(f"{ts()} {c('ERR ', RED, BOLD)}  {m}")


def log_step(m):
    print(f"\n{c('▶ ' + m, MAGENTA, BOLD)}")


def log_sub(m):
    print(f"  {c('·', DIM)} {m}")


def banner():
    print()
    print(c("╔══════════════════════════════════════════════════════╗", CYAN, BOLD))
    print(c("║        RETRY FAILED UPLOADS — Telegram Bot           ║", CYAN, BOLD))
    print(c("╚══════════════════════════════════════════════════════╝", CYAN, BOLD))
    print()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _download_video_to_temp(video_url: str) -> str:
    request = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        parsed_url = urlparse(video_url)
        suffix = Path(parsed_url.path).suffix or ".mp4"
        suffix = "".join(ch for ch in suffix if ch.isalnum() or ch in ".-_") or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(response.read())
            return tmp.name


def _send_video_to_chat(bot: telepot.Bot, chat_id: int | str, video_source, caption: str):
    if isinstance(video_source, (str, bytes)) and video_source.startswith("http"):
        source_path = _download_video_to_temp(video_source)
        try:
            with open(source_path, "rb") as video_file:
                return bot.sendVideo(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    parse_mode=PARSE_MODE,
                )
        finally:
            Path(source_path).unlink(missing_ok=True)

    return bot.sendVideo(
        chat_id=chat_id,
        video=video_source,
        caption=caption,
        parse_mode=PARSE_MODE,
    )


def extract_tweet_id(post_link: str) -> str | None:
    """Pull the numeric tweet ID from the end of a post_link URL."""
    parts = post_link.rstrip("/").split("/")
    for part in reversed(parts):
        if part.isdigit():
            return part
    return None


def extract_username(post_link: str) -> str:
    """Pull @username from https://x.com/Username/status/..."""
    try:
        # e.g. https://x.com/Bootyclapper187/status/2066145...
        parts = post_link.rstrip("/").split("/")
        # find 'status' index and go one back
        idx = parts.index("status")
        return parts[idx - 1]
    except (ValueError, IndexError):
        return "unknown"


def find_failed_csvs(args: list[str]) -> list[str]:
    if args:
        return args
    return sorted(glob.glob(os.path.join(FAILED_DIR, "failed_uploads_*.csv")))


def load_all_failed_entries(csv_files: list[str]) -> list[dict]:
    """Read all failed_uploads CSVs, deduplicate by tweet_id."""
    seen = set()
    entries = []
    for path in csv_files:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            for row in csv.DictReader(fh):
                link = (row.get("post_link") or "").strip()
                tweet_id = extract_tweet_id(link)
                if not tweet_id or tweet_id in seen:
                    continue
                seen.add(tweet_id)
                entries.append(
                    {
                        "tweet_id": tweet_id,
                        "post_link": link,
                        "user_display_name": (
                            row.get("user_display_name") or ""
                        ).strip(),
                        "description": (row.get("description") or "").strip(),
                        "source_file": os.path.basename(path),
                    }
                )
    return entries


def fetch_video(tweet_id: str) -> Video | None:
    return Video.objects(video_id=tweet_id).first()


def already_delivered(video: Video) -> bool:
    return bool(video.trials) and video.trials[-1].status == "completed"


def log_trial(
    video: Video,
    status: str,
    duration: float,
    error: str = "",
    file_id: str = "",
    msg_id: str = "",
):
    delivered = status == "completed"
    trial = TrialLog(
        mechanism_name="mechanism_2",
        attempt_number=len(video.trials) + 1,
        status=status,
        duration_seconds=duration,
        error_message=error,
        bot_sent=delivered,
        channel_sent=delivered,
        telegram_file_id=file_id,
        channel_message_id=msg_id,
    ).save()
    video.trials.append(trial)
    video.save()
    return trial


def send_video(bot: telepot.Bot, video: Video) -> dict:
    """
    Build caption from Video document and send to both channels.
    Returns dict with file_id, main_message_id, private_message_id, size_mb, duration.
    """
    username = video.uploader_username or "unknown"
    display_name = video.uploader_display_name or username
    tweet_url = video.tweet_url or f"https://x.com/{username}/status/{video.video_id}"
    title = video.title or video.text or "Video"
    text = video.text or video.description or ""

    caption = (
        f"🎬 *{title}*\n\n"
        f"{text}\n\n"
        f"👤 [{display_name}](https://x.com/{username})\n\n"
        f"[View on X]({tweet_url})"
    )

    res_main = _send_video_to_chat(
        bot=bot,
        chat_id=TELEGRAM_CHAT_ID,
        video_source=video.video_url,
        caption=caption,
    )

    main_file_id = res_main["video"]["file_id"]
    main_msg_id = res_main["message_id"]

    try:
        res_private = _send_video_to_chat(
            bot=bot,
            chat_id=PRIVATE_CHANNEL_ID,
            video_source=main_file_id,
            caption=caption,
        )
        private_msg_id = res_private["message_id"]
    except Exception as channel_error:
        copied = bot.copyMessage(
            chat_id=PRIVATE_CHANNEL_ID,
            from_chat_id=TELEGRAM_CHAT_ID,
            message_id=main_msg_id,
            caption=caption,
            parse_mode=PARSE_MODE,
        )
        private_msg_id = copied["message_id"]
        print(
            f"⚠️ [CHANNEL] Direct sendVideo(file_id) failed during retry; copied bot message instead. "
            f"Reason: {channel_error}"
        )

    return {
        "file_id": main_file_id,
        "main_message_id": main_msg_id,
        "private_message_id": private_msg_id,
        "size_mb": res_main["video"]["file_size"] / (1024 * 1024),
        "duration": res_main["video"].get("duration", 0),
    }


def _fail_row(entry: dict, error: str) -> dict:
    return {
        "user_display_name": entry["user_display_name"],
        "description": entry["description"],
        "post_link": entry["post_link"],
        "tweet_id": entry["tweet_id"],
        "error": error,
    }


def write_second_fails(failures: list[dict]):
    if not failures:
        log_ok("No second-attempt failures — everything retried successfully!")
        return
    ts_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = os.path.join(FAILED_DIR, f"second_fail_{ts_str}.csv")
    fields = ["user_display_name", "description", "post_link", "tweet_id", "error"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(failures)
    log_warn(f"Second-fail log saved → {c(out, YELLOW, BOLD)}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    banner()

    # ── 1. Connect DB ─────────────────────────────────────────────────────────
    log_step("Connecting to MongoDB")
    log_ok(f"Connected → {c(Video._get_collection().full_name, WHITE, BOLD)}")

    # ── 2. Init Telegram bot ──────────────────────────────────────────────────
    log_step("Initialising Telegram bot")
    try:
        bot = telepot.Bot(TELEGRAM_TOKEN)
        me = bot.getMe()
        log_ok(f"Bot ready → {c('@' + me['username'], WHITE, BOLD)}")
    except Exception as e:
        log_err(f"Telegram init failed: {e}")
        sys.exit(1)

    # ── 3. Find & load all failed CSVs ───────────────────────────────────────
    log_step("Loading failed upload CSVs")
    csv_files = find_failed_csvs(sys.argv[1:])
    if not csv_files:
        log_warn(f"No failed_uploads_*.csv files found in ./{FAILED_DIR}/")
        return

    log_ok(f"Found {c(len(csv_files), GREEN, BOLD)} failed upload file(s):")
    for f in csv_files:
        log_sub(f)

    entries = load_all_failed_entries(csv_files)
    log_ok(f"{c(len(entries), GREEN, BOLD)} unique failed entries loaded")

    if not entries:
        log_warn("Nothing to retry.")
        return

    # ── 4. Retry each entry ───────────────────────────────────────────────────
    log_step(f"Retrying {len(entries)} uploads …")

    second_fails = []
    succeeded = 0
    skipped_no_db = 0
    skipped_no_url = 0
    skipped_done = 0

    for idx, entry in enumerate(entries, start=1):
        tweet_id = entry["tweet_id"]
        print()
        print(
            c(
                f"  ─── [{idx}/{len(entries)}]  tweet_id={tweet_id}  ({entry['source_file']})",
                DIM,
            )
        )

        # Fetch from MongoDB
        video = fetch_video(tweet_id)
        if not video:
            log_warn(f"  Not found in MongoDB — skipping  (id={tweet_id})")
            skipped_no_db += 1
            second_fails.append(_fail_row(entry, "not found in MongoDB"))
            continue

        if already_delivered(video):
            log_sub(f"Already delivered — skipping  (id={tweet_id})")
            skipped_done += 1
            continue

        if not video.video_url:
            log_warn(f"  video_url is empty in DB — cannot send  (id={tweet_id})")
            skipped_no_url += 1
            second_fails.append(_fail_row(entry, "video_url is empty in DB"))
            continue

        log_sub(f"video_url = {c(video.video_url[:72] + '…', DIM)}")

        start = time.time()
        try:
            result = send_video(bot, video)
            duration = time.time() - start

            # Update Video document
            video.size_mb = result["size_mb"]
            video.duration_seconds = result["duration"]
            video.completed_at = datetime.now(timezone.utc)
            video.message_id_main = str(result["main_message_id"])
            video.message_id_private = str(result["private_message_id"])
            video.save()

            log_trial(
                video,
                status="completed",
                duration=duration,
                file_id=result["file_id"],
                msg_id=str(result["private_message_id"]),
            )

            log_ok(
                f"  ✅ Sent!  size={result['size_mb']:.1f}MB  "
                f"dur={result['duration']}s  "
                f"main_msg={result['main_message_id']}"
            )
            succeeded += 1

        except Exception as e:
            duration = time.time() - start
            error_str = str(e)

            log_trial(video, status="failed", duration=duration, error=error_str)

            log_err(f"  ❌ Failed: {error_str[:120]}")

            second_fails.append(_fail_row(entry, error_str))

        time.sleep(DELAY_BETWEEN)

    # ── 5. Write second-fail CSV ──────────────────────────────────────────────
    log_step("Saving results")
    write_second_fails(second_fails)

    # ── 6. Summary ────────────────────────────────────────────────────────────
    total = len(entries)
    print()
    print(c("╔══════════════════════════════════════════════════════╗", CYAN, BOLD))
    print(c("║                   RETRY SUMMARY                     ║", CYAN, BOLD))
    print(c("╠══════════════════════════════════════════════════════╣", CYAN, BOLD))
    print(c(f"║  Total entries        : {str(total).ljust(28)}║", WHITE))
    print(c(f"║  ✅ Succeeded          : {str(succeeded).ljust(28)}║", GREEN))
    print(
        c(
            f"║  ❌ Still failing      : {str(len(second_fails)).ljust(28)}║",
            RED if second_fails else DIM,
        )
    )
    print(c(f"║  ⏭  Already delivered  : {str(skipped_done).ljust(28)}║", DIM))
    print(c(f"║  ⚠  No DB record       : {str(skipped_no_db).ljust(28)}║", YELLOW))
    print(c(f"║  ⚠  No video_url in DB : {str(skipped_no_url).ljust(28)}║", YELLOW))
    print(c("╚══════════════════════════════════════════════════════╝", CYAN, BOLD))
    print()


if __name__ == "__main__":
    main()
