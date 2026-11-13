"""
fetch/fetch_likes.py — download your own X likes into scrapped/New Data.csv,
in the same 27-column format the pipeline expects. See WORKFLOW.md.

    python -m fetch.fetch_likes                # new likes, down to the last uploaded batch
    python -m fetch.fetch_likes --all          # every like X will return
    python -m fetch.fetch_likes --max-pages 3  # stop after 3 pages (testing)
    python -m fetch.fetch_likes --limit 3000   # raise the safety cap (default 1000 likes)

Login uses your browser session cookies, X_AUTH_TOKEN and X_CT0 in
core/constants.py. If X rotates ct0, the new value is saved back there.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.common import CLUSTER_MIN, CLUSTER_WINDOW, find_cut_index, find_latest_old_cleaned, recent_uploaded_ids  # noqa: E402,E501

CONSTANTS_PATH = ROOT / "core" / "constants.py"
SCRAPPED_DIR = ROOT / "scrapped"
DEFAULT_OUT = SCRAPPED_DIR / "New Data.csv"
RAW_DUMP = SCRAPPED_DIR / "response.json"

COLUMNS = [
    "tweet_type", "id", "created_at", "username", "user_display_name", "text", "lang", "source",
    "retweet_count", "favorite_count", "reply_count", "quote_count", "bookmark_count", "view_count",
    "has_media", "media_type", "media_urls", "video_url", "video_duration", "thumbnail_url",
    "conversation_id_str", "in_reply_to_status_id_str", "in_reply_to_user_id_str",
    "in_reply_to_screen_name", "quoted_status_id_str", "quoted_user_id_str", "retweeted_status_id_str",
]

# The public bearer token x.com's own web app sends with every API call.
WEB_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
PAGE_SIZE = 100
PAGE_DELAY = 1.5  # seconds between pages, to stay well under the rate limit
LOOKUP_DELAY = 1.0  # seconds between single-post lookups for linked videos
DEFAULT_LIMIT = 1000  # safety cap on likes per run, in case the last batch is never found

# Used only if the Likes query can't be found in x.com's JavaScript.
FALLBACK_QUERY_ID = "aeJWz--kknVBOl7wQ7gh7Q"
FALLBACK_FEATURES = [
    "rweb_video_screen_enabled", "profile_label_improvements_pcf_label_in_post_enabled",
    "rweb_tipjar_consumption_enabled", "verified_phone_label_enabled",
    "creator_subscriptions_tweet_preview_api_enabled", "responsive_web_graphql_timeline_navigation_enabled",
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled", "premium_content_api_read_enabled",
    "communities_web_enable_tweet_community_results_fetch", "c9s_tweet_anatomy_moderator_badge_enabled",
    "responsive_web_grok_analyze_button_fetch_trends_enabled", "responsive_web_grok_analyze_post_followups_enabled",
    "responsive_web_jetfuel_frame", "responsive_web_grok_share_attachment_enabled", "articles_preview_enabled",
    "responsive_web_edit_tweet_api_enabled", "graphql_is_translatable_rweb_tweet_is_translatable_enabled",
    "view_counts_everywhere_api_enabled", "longform_notetweets_consumption_enabled",
    "responsive_web_twitter_article_tweet_consumption_enabled", "tweet_awards_web_tipping_enabled",
    "responsive_web_grok_show_grok_translated_post", "responsive_web_grok_analysis_button_from_backend",
    "creator_subscriptions_quote_tweet_preview_enabled", "freedom_of_speech_not_reach_fetch_enabled",
    "standardized_nudges_misinfo", "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled",
    "longform_notetweets_rich_text_read_enabled", "longform_notetweets_inline_media_enabled",
    "responsive_web_grok_image_annotation_enabled", "responsive_web_enhance_cards_enabled",
]


class FetchError(Exception):
    pass


class SessionExpired(FetchError):
    pass


SESSION_EXPIRED_HELP = (
    "X session expired or invalid. Open x.com in your browser (logged in), copy the "
    "auth_token and ct0 cookies from DevTools → Application → Cookies → https://x.com, "
    "and paste them into X_AUTH_TOKEN / X_CT0 in core/constants.py."
)


# ── Credentials ──────────────────────────────────────────────────────────────


def load_credentials() -> tuple[str, str, str | None, str | None]:
    try:
        from core import constants
    except ImportError:
        raise FetchError("core/constants.py not found. Copy core/constants.example.py and fill it in.")

    auth_token = getattr(constants, "X_AUTH_TOKEN", "") or ""
    ct0 = getattr(constants, "X_CT0", "") or ""
    if not auth_token or not ct0 or "your-" in auth_token or "your-" in ct0:
        raise FetchError(
            "X_AUTH_TOKEN and X_CT0 are not set in core/constants.py. " + SESSION_EXPIRED_HELP.split(". ", 1)[1]
        )
    return (
        auth_token.strip(),
        ct0.strip(),
        (str(getattr(constants, "X_USER_ID", "") or "").strip() or None),
        (getattr(constants, "X_LIKES_QUERY_ID", "") or "").strip() or None,
    )


def persist_ct0(new_ct0: str) -> None:
    """Write a rotated ct0 back to core/constants.py so the next run uses it."""
    try:
        text = CONSTANTS_PATH.read_text(encoding="utf-8")
        updated, n = re.subn(
            r'^(X_CT0\s*=\s*)(["\']).*?\2',
            lambda m: f'{m.group(1)}"{new_ct0}"',
            text,
            count=1,
            flags=re.M,
        )
        if n:
            CONSTANTS_PATH.write_text(updated, encoding="utf-8")
            print("🔑 X rotated the ct0 cookie; saved the new value to core/constants.py", flush=True)
    except OSError as exc:
        print(f"⚠️ Couldn't save the rotated ct0 to constants.py: {exc}", flush=True)


# ── HTTP client ──────────────────────────────────────────────────────────────


class XClient:
    def __init__(self, auth_token: str, ct0: str):
        self.ct0 = ct0
        self.s = requests.Session()
        self.s.cookies.set("auth_token", auth_token, domain=".x.com")
        self.s.cookies.set("ct0", ct0, domain=".x.com")
        self.s.headers.update({"user-agent": USER_AGENT, "accept-language": "en-US,en;q=0.9"})

    def _api_headers(self) -> dict:
        return {
            "authorization": f"Bearer {WEB_BEARER}",
            "x-csrf-token": self.ct0,
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "content-type": "application/json",
            "referer": "https://x.com/",
            "origin": "https://x.com",
        }

    def _track_ct0(self, resp: requests.Response) -> None:
        new = resp.cookies.get("ct0")
        if new and new != self.ct0:
            self.ct0 = new
            persist_ct0(new)

    def get_page(self, url: str) -> requests.Response:
        resp = self.s.get(url, timeout=30)
        self._track_ct0(resp)
        return resp

    def get_api(self, url: str, params: dict) -> requests.Response:
        """GET an API endpoint, waiting out rate limits and retrying server errors."""
        for attempt in range(5):
            try:
                resp = self.s.get(url, params=params, headers=self._api_headers(), timeout=30)
            except requests.RequestException as exc:
                wait = 5 * (attempt + 1)
                print(f"⚠️ Network error ({exc}); retrying in {wait}s", flush=True)
                time.sleep(wait)
                continue

            self._track_ct0(resp)
            if resp.status_code == 429:
                reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
                wait = max(reset - int(time.time()), 5) + 2
                print(f"⏳ Rate limited by X; waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 5 * (attempt + 1)
                print(f"⚠️ X returned {resp.status_code}; retrying in {wait}s", flush=True)
                time.sleep(wait)
                continue
            return resp
        raise FetchError("X kept failing after 5 attempts; try again later.")


# ── Discovering the Likes endpoint ───────────────────────────────────────────


def _parse_name_list(raw: str) -> list[str]:
    return re.findall(r'"([^"]+)"', raw)


def bootstrap(client: XClient, user_id: str | None, query_id_override: str | None) -> dict:
    """Load x.com once to get your user id, the Likes query id and its feature flags."""
    resp = client.get_page("https://x.com/home")
    if resp.status_code in (401, 403) or "/login" in resp.url or "/i/flow/login" in resp.url:
        raise SessionExpired(SESSION_EXPIRED_HELP)
    html = resp.text

    if not user_id:
        m = re.search(r'"session":\{[^{}]*?"user_id":"(\d+)"', html) or re.search(r'"user_id":"(\d+)"', html)
        if m:
            user_id = m.group(1)
        else:
            twid = client.s.cookies.get("twid") or ""
            m = re.search(r"u(?:=|%3D)(\d+)", twid)
            user_id = m.group(1) if m else None
    if not user_id:
        raise SessionExpired(
            "Couldn't find your user id on x.com, which usually means the session is invalid. "
            + SESSION_EXPIRED_HELP
            + " (If the cookies are fresh, also set X_USER_ID: the number in your twid cookie after 'u%3D'.)"
        )

    main_js = re.search(r"https://abs\.twimg\.com/responsive-web/client-web/main\.[\w.]+\.js", html)
    js = client.get_page(main_js.group(0)).text if main_js else ""

    likes = find_operation(js, html, "Likes")
    if query_id_override:
        likes = likes or make_operation("Likes", query_id_override, FALLBACK_FEATURES, [], html)
        likes["query_id"] = query_id_override
    if not likes:
        print("⚠️ Couldn't find the Likes query in x.com's JavaScript; using the built-in fallback.", flush=True)
        likes = make_operation("Likes", FALLBACK_QUERY_ID, FALLBACK_FEATURES, [], html)

    # Used to fetch the video of a post that a liked post only links to.
    tweet_lookup = find_operation(js, html, "TweetResultByRestId")
    if not tweet_lookup:
        print(
            "⚠️ Couldn't find the single-post query in x.com's JavaScript; "
            "videos that liked posts only link to will be left out this run.",
            flush=True,
        )

    return {"user_id": user_id, "likes": likes, "tweet_lookup": tweet_lookup}


def make_operation(name: str, query_id: str, feature_names: list[str], toggle_names: list[str], html: str) -> dict:
    # Use the same on/off values the web app has for this account, defaulting to on.
    features = {}
    for feature in feature_names:
        m = re.search(rf'"{re.escape(feature)}":\{{"value":(true|false)', html)
        features[feature] = (m.group(1) == "true") if m else True
    return {
        "name": name,
        "query_id": query_id,
        "features": features,
        "field_toggles": {toggle: False for toggle in toggle_names},
    }


def find_operation(js: str, html: str, name: str) -> dict | None:
    m = re.search(
        rf'queryId:"([\w-]+)",operationName:"{name}",operationType:"query",'
        r"metadata:\{featureSwitches:\[([^\]]*)\],fieldToggles:\[([^\]]*)\]",
        js,
    )
    if not m:
        return None
    return make_operation(name, m.group(1), _parse_name_list(m.group(2)), _parse_name_list(m.group(3)), html)


def graphql_get(client: XClient, op: dict, variables: dict) -> dict:
    url = f"https://x.com/i/api/graphql/{op['query_id']}/{op['name']}"

    for _ in range(3):
        params = {
            "variables": json.dumps(variables, separators=(",", ":")),
            "features": json.dumps(op["features"], separators=(",", ":")),
        }
        if op["field_toggles"]:
            params["fieldToggles"] = json.dumps(op["field_toggles"], separators=(",", ":"))

        resp = client.get_api(url, params)
        if resp.status_code in (401, 403):
            raise SessionExpired(SESSION_EXPIRED_HELP + f" (HTTP {resp.status_code}: {resp.text[:200]})")
        if resp.status_code == 400:
            # X lists any feature flags it now requires; add them and try again.
            missing = re.search(r"cannot be null: ([\w, ]+)", resp.text)
            if missing:
                for name in missing.group(1).split(","):
                    op["features"][name.strip()] = True
                continue
        if resp.status_code == 404:
            raise FetchError(
                f"X returned 404 for the {op['name']} query id {op['query_id']!r}; it has probably changed. "
                "Remove X_LIKES_QUERY_ID from constants.py if you set it, and re-run."
            )
        if resp.status_code != 200:
            raise FetchError(f"X returned HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        if not data.get("data") and data.get("errors"):
            message = "; ".join(e.get("message", "") for e in data["errors"])
            if any(e.get("code") in (32, 89, 215, 239, 353) for e in data["errors"]):
                raise SessionExpired(SESSION_EXPIRED_HELP + f" ({message})")
            raise FetchError(f"X returned an error: {message}")
        return data
    raise FetchError(f"X kept rejecting the {op['name']} request's feature flags.")


def fetch_tweet(client: XClient, cfg: dict, tweet_id: str) -> dict | None:
    """One post by id, or None if it's deleted, protected or unavailable."""
    data = graphql_get(
        client,
        cfg["tweet_lookup"],
        {"tweetId": tweet_id, "withCommunity": False, "includePromotedContent": False, "withVoice": False},
    )
    return unwrap_tweet(((data.get("data") or {}).get("tweetResult") or {}).get("result"))


def fetch_likes_page(client: XClient, cfg: dict, cursor: str | None) -> dict:
    variables = {
        "userId": cfg["user_id"],
        "count": PAGE_SIZE,
        "includePromotedContent": False,
        "withClientEventToken": False,
        "withBirdwatchNotes": False,
        "withVoice": True,
    }
    if cursor:
        variables["cursor"] = cursor
    return graphql_get(client, cfg["likes"], variables)


# ── Parsing the timeline ─────────────────────────────────────────────────────


def parse_timeline(data: dict) -> tuple[list[dict], str | None]:
    """Return (tweet results in like order, bottom cursor) from a Likes response."""
    user = ((data.get("data") or {}).get("user") or {}).get("result") or {}
    timeline = (user.get("timeline") or user.get("timeline_v2") or {}).get("timeline") or {}

    tweets, cursor = [], None
    for ins in timeline.get("instructions", []):
        entries = ins.get("entries") or ([ins["entry"]] if ins.get("entry") else [])
        for entry in entries:
            content = entry.get("content") or {}
            if content.get("cursorType") == "Bottom" or entry.get("entryId", "").startswith("cursor-bottom"):
                cursor = content.get("value") or cursor
                continue
            result = ((content.get("itemContent") or {}).get("tweet_results") or {}).get("result")
            tweet = unwrap_tweet(result)
            if tweet:
                tweets.append(tweet)
    return tweets, cursor


def unwrap_tweet(result: dict | None) -> dict | None:
    if not result:
        return None
    if result.get("__typename") == "TweetWithVisibilityResults" or ("tweet" in result and "legacy" not in result):
        result = result.get("tweet") or {}
    return result if result.get("legacy") else None


def _user_fields(tweet: dict) -> tuple[str, str]:
    user = ((tweet.get("core") or {}).get("user_results") or {}).get("result") or {}
    core, legacy = user.get("core") or {}, user.get("legacy") or {}
    return (
        core.get("screen_name") or legacy.get("screen_name") or "",
        core.get("name") or legacy.get("name") or "",
    )


def _clean_text(text: str, url_entities: list[dict], media: list[dict]) -> str:
    """Expand t.co links and drop the trailing media link, like the old export did."""
    for u in url_entities:
        if u.get("url"):
            text = text.replace(u["url"], u.get("expanded_url") or u["url"])
    for m in media:
        if m.get("url"):
            text = text.replace(m["url"], "")
    return text.strip()


def _best_mp4(media: dict) -> str | None:
    variants = [
        v for v in (media.get("video_info") or {}).get("variants", [])
        if v.get("content_type") == "video/mp4" and v.get("url")
    ]
    if not variants:
        return None
    return max(variants, key=lambda v: v.get("bitrate") or 0)["url"]


def _str(value) -> str | None:
    """CSV value: None for missing/empty (written unquoted), else a string."""
    if value is None or value == "":
        return None
    return str(value)


def _tweet_media(tweet: dict) -> list[dict]:
    legacy = tweet.get("legacy") or {}
    return (legacy.get("extended_entities") or {}).get("media") or (legacy.get("entities") or {}).get("media") or []


def media_fields(media: list[dict], video_index: int = 0) -> dict:
    """The media columns of a row; video_index picks which video (0-based) becomes video_url."""
    videos = [m for m in media if m.get("type") in ("video", "animated_gif")]
    video = videos[min(max(video_index, 0), len(videos) - 1)] if videos else None
    duration_ms = ((video or {}).get("video_info") or {}).get("duration_millis")
    return {
        "has_media": "true" if media else "false",
        "media_type": "video" if videos else ("photo" if media else "none"),
        "media_urls": "; ".join(m["media_url_https"] for m in media if m.get("media_url_https")),
        "video_url": _best_mp4(video) if video else None,
        "video_duration": round(duration_ms / 1000) if duration_ms else None,
        "thumbnail_url": (video or {}).get("media_url_https"),
    }


# A liked post whose only video is a link to another post's video.
LINKED_VIDEO_RE = re.compile(r"https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/\w+/status/(\d+)/video/(\d+)")


def fill_linked_videos(client: XClient, cfg: dict, rows: list[dict], cache: dict) -> int:
    """For rows with no video that link to ".../status/<id>/video/<n>", take that post's video.
    The row keeps the liked post's id and text; only the media columns come from the linked post."""
    if not cfg.get("tweet_lookup"):
        return 0
    filled = 0
    for row in rows:
        if row["video_url"] or not row["text"]:
            continue
        m = LINKED_VIDEO_RE.search(row["text"])
        if not m:
            continue
        linked_id, n = m.group(1), int(m.group(2))
        if linked_id not in cache:
            try:
                cache[linked_id] = fetch_tweet(client, cfg, linked_id)
            except SessionExpired:
                raise
            except FetchError as exc:
                print(f"⚠️ Couldn't look up linked post {linked_id}: {exc}", flush=True)
                cache[linked_id] = None
            time.sleep(LOOKUP_DELAY)
        linked = cache[linked_id]
        fields = media_fields(_tweet_media(linked), n - 1) if linked else {}
        if fields.get("video_url"):
            row.update({k: _str(v) for k, v in fields.items()})
            filled += 1
        else:
            print(f"ℹ️ Post {row['id']} links to a video in {linked_id}, which is unavailable", flush=True)
    return filled


def tweet_to_row(tweet: dict) -> dict:
    legacy = tweet["legacy"]
    username, display_name = _user_fields(tweet)

    note = ((tweet.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}
    media = _tweet_media(tweet)
    if note.get("text"):
        text = _clean_text(note["text"], (note.get("entity_set") or {}).get("urls", []), media)
    else:
        text = _clean_text(legacy.get("full_text", ""), (legacy.get("entities") or {}).get("urls", []), media)

    retweeted = unwrap_tweet((legacy.get("retweeted_status_result") or {}).get("result"))
    quoted = unwrap_tweet((tweet.get("quoted_status_result") or {}).get("result"))
    quoted_id = legacy.get("quoted_status_id_str")
    if retweeted:
        tweet_type = "retweet"
    elif legacy.get("is_quote_status") and quoted_id:
        tweet_type = "quote"
    elif legacy.get("in_reply_to_status_id_str"):
        tweet_type = "reply"
    else:
        tweet_type = "original"


    created = datetime.strptime(legacy["created_at"], "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)

    row = {
        "tweet_type": tweet_type,
        "id": legacy.get("id_str") or tweet.get("rest_id"),
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "username": username,
        "user_display_name": display_name,
        "text": text,
        "lang": legacy.get("lang"),
        "source": tweet.get("source"),
        "retweet_count": legacy.get("retweet_count", 0),
        "favorite_count": legacy.get("favorite_count", 0),
        "reply_count": legacy.get("reply_count", 0),
        "quote_count": legacy.get("quote_count", 0),
        "bookmark_count": legacy.get("bookmark_count", 0),
        "view_count": (tweet.get("views") or {}).get("count"),
        **media_fields(media),
        "conversation_id_str": legacy.get("conversation_id_str"),
        "in_reply_to_status_id_str": legacy.get("in_reply_to_status_id_str"),
        "in_reply_to_user_id_str": legacy.get("in_reply_to_user_id_str"),
        "in_reply_to_screen_name": legacy.get("in_reply_to_screen_name"),
        "quoted_status_id_str": quoted_id,
        "quoted_user_id_str": (quoted or {}).get("legacy", {}).get("user_id_str"),
        "retweeted_status_id_str": (retweeted or {}).get("rest_id"),
    }
    out = {col: _str(row[col]) for col in COLUMNS}
    out["text"] = text  # the old export wrote empty text as "" rather than a bare blank
    return out


# ── Output ───────────────────────────────────────────────────────────────────


def _csv_field(value: str | None) -> str:
    if value is None:
        return ""
    return '"' + value.replace('"', '""') + '"'


def write_csv(rows: list[dict], path: Path) -> None:
    """Same layout as the old export: every non-empty field quoted, empty fields bare."""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(_csv_field(c) for c in COLUMNS) + "\n")
        for row in rows:
            handle.write(",".join(_csv_field(row[c]) for c in COLUMNS) + "\n")
    os.replace(tmp, path)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Download your X likes into scrapped/New Data.csv")
    parser.add_argument("--all", action="store_true", help="fetch every like, ignoring the last uploaded batch")
    parser.add_argument("--max-pages", type=int, default=0, help="stop after this many pages (0 = no limit)")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"stop after this many likes (default {DEFAULT_LIMIT}; no cap with --all; 0 = no cap)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output CSV (default: scrapped/New Data.csv)")
    parser.add_argument("--save-raw", action="store_true", help="also save the raw API pages to scrapped/response.json")
    args = parser.parse_args()
    limit = args.limit if args.limit is not None else (0 if args.all else DEFAULT_LIMIT)

    try:
        auth_token, ct0, user_id, query_id = load_credentials()
        client = XClient(auth_token, ct0)
        cfg = bootstrap(client, user_id, query_id)
        print(f"🔐 Logged in as user {cfg['user_id']} · Likes query {cfg['likes']['query_id']}", flush=True)

        anchors = set() if args.all else set(recent_uploaded_ids(str(SCRAPPED_DIR)))
        latest = find_latest_old_cleaned(str(SCRAPPED_DIR))
        anchor_file = os.path.basename(latest) if latest else None
        if anchors:
            print(
                f"⚓ Stopping once your last uploaded batch ({anchor_file}) is reached: "
                f"{CLUSTER_MIN} of your {len(anchors)} most recent uploads within {CLUSTER_WINDOW} likes",
                flush=True,
            )
        else:
            print("📚 Fetching all likes (no earlier batch to stop at)", flush=True)

        rows: list[dict] = []
        raw_pages: list[dict] = []
        seen: set[str] = set()
        linked_cache: dict = {}
        linked_total = 0
        cut = None
        cursor, page = None, 0
        stopped_early = False
        hit_limit = False

        while True:
            page += 1
            data = fetch_likes_page(client, cfg, cursor)
            if args.save_raw:
                raw_pages.append(data)
            tweets, next_cursor = parse_timeline(data)

            new_rows = []
            for tweet in tweets:
                try:
                    row = tweet_to_row(tweet)
                except (KeyError, ValueError, TypeError) as exc:
                    print(f"⚠️ Skipped a post that couldn't be parsed ({exc!r})", flush=True)
                    continue
                if row["id"] not in seen:
                    seen.add(row["id"])
                    new_rows.append(row)
            linked = fill_linked_videos(client, cfg, new_rows, linked_cache)
            linked_total += linked
            rows.extend(new_rows)

            videos = sum(1 for r in rows if r["video_url"])
            linked_note = f", {linked} via linked posts" if linked else ""
            print(f"📄 Page {page}: +{len(new_rows)} likes ({len(rows)} total, {videos} with video{linked_note})", flush=True)

            if anchors:
                ids = [r["id"] for r in rows]
                cut = find_cut_index(ids, anchors)
                # Fetch a full window past the cut so Pipe 1 sees the same cluster.
                if cut is not None and len(rows) >= cut + CLUSTER_WINDOW:
                    matched = sum(1 for x in ids[cut : cut + CLUSTER_WINDOW] if x in anchors)
                    print(
                        f"⚓ Reached the last uploaded batch at like #{cut + 1}: {cut} new likes above it "
                        f"({matched} recent uploads matched nearby)",
                        flush=True,
                    )
                    break
            if not new_rows or not next_cursor or next_cursor == cursor:
                print("🏁 Reached the end of your likes", flush=True)
                break
            if limit and len(rows) >= limit and cut is None:
                del rows[limit:]
                print(f"🛑 Hit the {limit}-like limit without reaching the last uploaded batch", flush=True)
                hit_limit = True
                break
            if args.max_pages and page >= args.max_pages:
                print(f"⏹ Stopped after {page} pages (--max-pages)", flush=True)
                stopped_early = True
                break
            cursor = next_cursor
            time.sleep(PAGE_DELAY)

        if args.save_raw:
            RAW_DUMP.write_text(json.dumps(raw_pages, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"🧾 Raw API pages saved to {RAW_DUMP.relative_to(ROOT)}", flush=True)

        if not rows:
            raise FetchError("X returned no likes at all; nothing was written.")

        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_csv(rows, args.out)
        videos = sum(1 for r in rows if r["video_url"])
        linked_note = f", {linked_total} of them from linked posts" if linked_total else ""
        print(f"✅ Wrote {len(rows)} likes ({videos} with video{linked_note}) to {args.out}", flush=True)

        seen_anchors = sum(1 for r in rows if r["id"] in anchors)
        if hit_limit and anchors and cut is None:
            print(
                f"❌ Stopped at {limit} likes without finding your last uploaded batch ({seen_anchors} of your "
                f"{len(anchors)} most recent uploads seen, none {CLUSTER_MIN} close together), so Pipe 1 can't "
                "cut this file. Either more than "
                f"{limit} likes are new (re-run with --limit {limit * 3}), or the last batch's posts are gone "
                "from your likes (unliked or deleted); check before uploading.",
                flush=True,
            )
            return 1
        if stopped_early and anchors and cut is None:
            print(
                f"ℹ️ Stopped before reaching {anchor_file} ({seen_anchors} recent uploads seen), "
                "so this file isn't ready for Pipe 1. That's fine for a test run.",
                flush=True,
            )
        elif anchors and cut is None:
            print(
                f"⚠️ Reached the end of your likes without finding your last uploaded batch ({seen_anchors} of "
                f"your {len(anchors)} most recent uploads seen), so Pipe 1 won't be able to cut this file.",
                flush=True,
            )
        return 0

    except FetchError as exc:
        print(f"❌ {exc}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
