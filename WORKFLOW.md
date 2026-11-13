# Upload Workflow

One command fetches your new liked posts from X, cleans them, uploads the videos to Telegram, records everything in MongoDB, retries failures, and writes a report.

```sh
venv\Scripts\activate
python run_full_workflow.py
```

The steps always run with `venv\Scripts\python.exe`, even if you start the script with your global Python.

## Before the first run

1. Make sure `core/constants.py` exists (copy `core/constants.example.py` and fill it in).
2. Paste your X login cookies into it once. Open x.com in your browser while logged in, go to DevTools → Application → Cookies → `https://x.com`, and copy:
   - `auth_token` → `X_AUTH_TOKEN`
   - `ct0` → `X_CT0`

   They last until you log out of that browser session or change your password. If X rotates `ct0`, the fetcher saves the new value for you. When the session does die, the run stops with "X session expired"; paste fresh cookies and re-run.

That's it. Don't export, rename or archive anything by hand; the workflow does that now.

## What `run_full_workflow.py` does

| Step | Script | What happens |
|---|---|---|
| 0 | `fetch/fetch_likes.py` | Downloads your likes (newest first) into **`scrapped/New Data.csv`**, stopping once it reaches the newest posts of the latest `N Old Cleaned.csv`, which are the last batch you uploaded. As a safety cap it stops after 1000 likes (`--limit` changes it); if it gets there without finding the last batch, it fails so the run stops before uploading. On a first run, with no batch yet, it just keeps the newest 1000. If a liked post has no video of its own but links to one (`x.com/<user>/status/<id>/video/<n>`), it looks up that post and uses its video; the row keeps the liked post's id and text. |
| 1 | `pipeline/run_all_pipes.py` | Runs Pipe 1–7 inside `scrapped/` and produces `New Cleaned.csv`, which is then renamed to **`Cleaned.csv`** and validated. If there are 0 new rows, the run stops here. |
| 2 | `upload/upload_videos.py` | Sends every row of `Cleaned.csv` to the bot chat and forwards it to the archive channel. Each video and attempt is logged to MongoDB, and failures go to `failed_uploads/failed_uploads_<time>.csv`. |
| — | *(archive)* | Copies `Cleaned.csv` to **`scrapped/<N+1> Old Cleaned.csv`**, which the next run uses as its anchor. |
| 3 | `maintenance/back_fill_url.py` | Sets `video_url` and `uploader_display_name` on this batch's Video docs, so failed uploads can be retried from the DB. |
| 4 | `maintenance/tag_stats.py` | Recalculates `total_videos`, `total_views` and `total_size_mb` for every tag. The upload step doesn't update these. |
| 5 | `maintenance/tag_relationships.py` | Recomputes the "related tags" collection (`tag_relationship`). |

At the end it writes **`reports/run_<time>/run_report.html`** (embedded failed posts and the full logs) and `run_report.txt`, plus copies of the run's failure CSVs.

Options:

- `--no-fetch`: skip step 0 and use the `scrapped/New Data.csv` that's already there (e.g. a manual export). The file must include the newest batch you already uploaded, because Pipe 1 cuts the new rows off above it.
- `--skip-tags`: skip steps 4–5 (they scan the whole collection and are the slowest part).

If step 0, 1 or 2 fails, the run stops and still writes a report. If step 2 crashes partway through, `Cleaned.csv` is **not** archived, so check the bot chat for videos that were already posted before you re-run. Steps 3–5 log a warning and the run keeps going.

## Retrying failed uploads (separate command)

Retrying is **not** part of the workflow. When a run has failures, it prints the command to retry them:

```sh
python retry_failed.py "failed_uploads/failed_uploads_<time>.csv"   # one run's failures
python retry_failed.py                                              # every failed_uploads_*.csv
```

It downloads each video and uploads the file instead of the URL (mechanism_2). Videos that were already delivered are skipped, so it's safe to run more than once. Anything that fails again goes to `failed_uploads/second_fail_<time>.csv`.

## The data pipeline (`pipeline/`)

All pipes read and write `scrapped/New Cleaned.csv` in place:

| Pipe | Purpose |
|---|---|
| `Pipe_1_Cut_New_Data.py` | Finds the top 5 rows of the latest `N Old Cleaned.csv` inside `New Data.csv` (at least 4 must match, close together) and keeps only the rows above them, which are the new likes. |
| `Pipe_2_Remove_Empty.py` | Drops rows with no `video_url`, adds them to `empty_url_dump.csv` (those ids are ignored from then on), dedupes by id, and trims columns after `conversation_id_str`. |
| `Pipe_3_Type_Check_Default.py` | Converts count columns to ints, with blanks becoming 0. |
| `Pipe_4_Tag.py` | Extracts hashtags into `tags`. |
| `Pipe_5_Keywords.py` | Extracts keywords with spaCy and YAKE. |
| `Pipe_6_U_IDS.py` | Assigns a `unique_id` (UUID) to each row. |
| `Pipe_7_Timestamp.py` | Assigns `fake_timestamp`/`fake_date` 5 minutes apart, continuing from the latest `N Old Cleaned.csv`. |

`pipeline/common.py` holds `find_latest_old_cleaned()`, which Pipe 1 and Pipe 7 use to find the anchor file.

## Running steps on their own

Run these from the project root. The `-m` form is required because the scripts import from `core/`.

```sh
python -m fetch.fetch_likes                            # fetch new likes into scrapped/New Data.csv
python -m fetch.fetch_likes --max-pages 1              #   ...just the newest page (quick login test)
python -m fetch.fetch_likes --limit 3000               #   ...raise the safety cap (default: stop after 1000 likes)
python -m fetch.fetch_likes --all                      #   ...every like, ignoring the last batch (no cap)
python -m fetch.fetch_likes --save-raw                 #   ...also dump raw API pages to scrapped/response.json
python pipeline/run_all_pipes.py                       # pipeline only (writes scrapped/New Cleaned.csv)
python -m upload.upload_videos                         # upload scrapped/Cleaned.csv
python -m maintenance.back_fill_url                    # backfill from the latest "N Old Cleaned.csv"
python -m maintenance.back_fill_url --all              #   ...or from every archived batch
python -m maintenance.back_fill_url "scrapped/12 Old Cleaned.csv"
python -m maintenance.tag_stats
python -m maintenance.tag_relationships
```

## Project layout

```
run_full_workflow.py     entry point (this document)
retry_failed.py          retry failed uploads (separate command)
core/                    config + shared modules
  constants.py             secrets: Telegram token/chat ids, MongoDB URI, X cookies (gitignored)
  constants.example.py     template for constants.py
  db.py                    mongoengine connection (import it to connect)
  bot.py                   telepot bot instance
  models.py                Video, Tag, TrialLog, TagRelationship
  generate_title.py        spaCy title generator used in captions
fetch/                   fetch_likes.py (downloads your likes from X into New Data.csv)
pipeline/                Pipe 1–7 + run_all_pipes.py + common.py
upload/                  upload_videos.py, send_x_videos.py, video_logger.py,
                         grab_vids.py (reads Cleaned.csv), failed_uploads_logger.py
maintenance/             back_fill_url.py, retry_failed_uploads.py, tag_stats.py, tag_relationships.py
scrapped/                DATA ONLY: New Data.csv, Cleaned.csv, "N Old Cleaned.csv", empty_url_dump.csv
failed_uploads/          failed_uploads_*.csv / second_fail_*.csv
reports/                 run_<time>/ reports
```
