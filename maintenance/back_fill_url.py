"""
back_fill_url.py
────────────────
Bulk-sets video_url and uploader_display_name on Video documents in MongoDB
from cleaned CSVs (matched by tweet id -> Video.video_id).

retry_failed_uploads.py resends from the DB, so a Video without video_url
cannot be retried. The workflow runs this on scrapped/Cleaned.csv after every
upload as a safety net.

Usage (from the project root):
    python -m maintenance.back_fill_url                      # latest "N Old Cleaned.csv"
    python -m maintenance.back_fill_url scrapped/Cleaned.csv  # specific file(s)
    python -m maintenance.back_fill_url --all                 # every "N Old Cleaned.csv"
"""

import csv
import glob
import os
import sys
from datetime import datetime

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

# ── CONFIG ────────────────────────────────────────────────────────────────────
CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scrapped")
BATCH_SIZE = 500
# ─────────────────────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
DIM = "\033[2m"


def c(text, *codes):
    return "".join(codes) + str(text) + RESET


def ts():
    return c(f"[{datetime.now().strftime('%H:%M:%S')}]", DIM)


def log_info(msg):
    print(f"{ts()} {c('INFO', BLUE, BOLD)}  {msg}")


def log_ok(msg):
    print(f"{ts()} {c('OK  ', GREEN, BOLD)}  {msg}")


def log_warn(msg):
    print(f"{ts()} {c('WARN', YELLOW, BOLD)}  {msg}")


def log_err(msg):
    print(f"{ts()} {c('ERR ', RED, BOLD)}  {msg}")


def log_step(msg):
    print(f"\n{c('▶ ' + msg, MAGENTA, BOLD)}")


def log_sub(msg):
    print(f"  {c('·', DIM)} {msg}")


def banner():
    print()
    print(c("╔══════════════════════════════════════════════════════╗", CYAN, BOLD))
    print(c("║     VIDEO URL BACKFILL  —  MongoDB Bulk Updater      ║", CYAN, BOLD))
    print(c("╚══════════════════════════════════════════════════════╝", CYAN, BOLD))
    print()


def _batch_number(path):
    name = os.path.basename(path).split(" ", 1)[0]
    return int(name) if name.isdigit() else -1


def find_csv_files(args):
    """CSV paths from argv; `--all` = every archived batch; default = latest batch."""
    if args and args != ["--all"]:
        return args
    files = [
        f
        for f in glob.glob(os.path.join(CSV_DIR, "* Old Cleaned.csv"))
        if _batch_number(f) >= 0
    ]
    files.sort(key=_batch_number)
    return files if args == ["--all"] else files[-1:]


def read_csv(path):
    mapping = {}
    skipped_no_url = 0
    skipped_no_id = 0

    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)

        if not reader.fieldnames:
            log_warn(f"Empty/unreadable: {os.path.basename(path)}")
            return mapping

        cols = set(reader.fieldnames)
        missing = {"id", "video_url", "user_display_name"} - cols
        if missing:
            log_warn(
                f"Missing columns {missing} in {os.path.basename(path)} — skipping"
            )
            return mapping

        for row in reader:
            vid_id = (row.get("id") or "").strip()
            vid_url = (row.get("video_url") or "").strip()
            display_name = (row.get("user_display_name") or "").strip()

            if not vid_id:
                skipped_no_id += 1
                continue
            if not vid_url:
                skipped_no_url += 1
                continue

            fields = {"video_url": vid_url}
            if display_name:
                fields["uploader_display_name"] = display_name
            mapping[vid_id] = fields

    if skipped_no_url or skipped_no_id:
        log_sub(
            f"Skipped: {c(skipped_no_url, YELLOW)} no URL  |  "
            f"{c(skipped_no_id, YELLOW)} no ID"
        )

    return mapping


def bulk_update(collection, mapping):
    items = list(mapping.items())
    total = len(items)
    matched = 0
    modified = 0
    errors = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = items[batch_start : batch_start + BATCH_SIZE]
        batch_end = min(batch_start + BATCH_SIZE, total)
        ops = [
            UpdateOne({"video_id": vid_id}, {"$set": fields})
            for vid_id, fields in batch
        ]

        log_sub(
            f"Batch {c(batch_start + 1, WHITE)}–{c(batch_end, WHITE)} / {c(total, WHITE)}  "
            f"({c(len(ops), CYAN)} ops) …"
        )

        try:
            result = collection.bulk_write(ops, ordered=False)
            matched += result.matched_count
            modified += result.modified_count
        except BulkWriteError as bwe:
            errs = bwe.details.get("writeErrors", [])
            errors += len(errs)
            matched += bwe.details.get("nMatched", 0)
            modified += bwe.details.get("nModified", 0)
            log_err(f"BulkWriteError — {len(errs)} failures in this batch")
            for e in errs[:3]:
                log_err(
                    f"  {e.get('errmsg', '?')}  (id={e.get('op', {}).get('q', {}).get('video_id', '?')})"
                )
            if len(errs) > 3:
                log_err(f"  … and {len(errs) - 3} more")

    return matched, modified, errors


def main():
    banner()

    # ── 1. Find CSVs ─────────────────────────────────────────────────────────
    log_step("Scanning for CSV files")
    csv_files = find_csv_files(sys.argv[1:])

    if not csv_files:
        log_err(f"No '* Old Cleaned.csv' files found in: {CSV_DIR}")
        sys.exit(1)

    log_ok(f"Found {c(len(csv_files), GREEN, BOLD)} CSV file(s)")
    for f in csv_files:
        log_sub(f)

    # ── 2. Connect ────────────────────────────────────────────────────────────
    log_step("Connecting to MongoDB")
    import core.db  # noqa: F401  establishes connection
    from core.models import Video

    col = Video._get_collection()
    log_ok(f"Connected  →  {c(col.full_name, WHITE, BOLD)}")

    # ── 3. Process each CSV ───────────────────────────────────────────────────
    grand_rows = 0
    grand_matched = 0
    grand_modified = 0
    grand_errors = 0
    file_stats = []

    for idx, csv_path in enumerate(csv_files, start=1):
        fname = os.path.basename(csv_path)
        print()
        print(c("─" * 62, DIM))
        log_step(f"[{idx}/{len(csv_files)}]  {fname}")

        log_info("Reading CSV …")
        mapping = read_csv(csv_path)
        rows = len(mapping)
        log_ok(f"{c(rows, GREEN, BOLD)} usable rows")

        if not mapping:
            log_warn("Nothing to update — skipping")
            file_stats.append((fname, 0, 0, 0, 0))
            continue

        grand_rows += rows

        log_info("Sending bulk updates to MongoDB …")
        m, mod, err = bulk_update(col, mapping)

        grand_matched += m
        grand_modified += mod
        grand_errors += err
        file_stats.append((fname, rows, m, mod, err))

        log_ok(
            f"Done →  matched={c(m, CYAN)}  "
            f"modified={c(mod, GREEN)}  "
            f"errors={c(err, RED if err else DIM)}"
        )

    # ── 4. Summary ────────────────────────────────────────────────────────────
    unmatched = grand_rows - grand_matched
    print()
    print(c("╔══════════════════════════════════════════════════════╗", CYAN, BOLD))
    print(c("║                   FINAL SUMMARY                     ║", CYAN, BOLD))
    print(c("╠══════════════════════════════════════════════════════╣", CYAN, BOLD))
    print(c(f"║  CSV files processed  : {str(len(csv_files)).ljust(28)}║", WHITE))
    print(c(f"║  Total rows parsed    : {str(grand_rows).ljust(28)}║", WHITE))
    print(c(f"║  Documents matched    : {str(grand_matched).ljust(28)}║", CYAN))
    print(c(f"║  Documents modified   : {str(grand_modified).ljust(28)}║", GREEN))
    print(c(f"║  Rows not in MongoDB  : {str(unmatched).ljust(28)}║", YELLOW))
    print(
        c(
            f"║  Bulk-write errors    : {str(grand_errors).ljust(28)}║",
            RED if grand_errors else DIM,
        )
    )
    print(c("╚══════════════════════════════════════════════════════╝", CYAN, BOLD))

    print()
    print(c("  Per-file breakdown:", BOLD))
    print(
        c(
            f"  {'File':<38} {'Rows':>6} {'Matched':>8} {'Modified':>9} {'Errors':>7}",
            DIM,
        )
    )
    print(c("  " + "─" * 72, DIM))
    for fname, rows, m, mod, err in file_stats:
        print(
            f"  {fname:<38} "
            f"{c(str(rows).rjust(6), WHITE)} "
            f"{c(str(m).rjust(8), CYAN)} "
            f"{c(str(mod).rjust(9), GREEN)} "
            f"{c(str(err).rjust(7), RED if err else DIM)}"
        )

    print()
    if grand_errors == 0:
        print(c("  ✓  Backfill complete with no errors!", GREEN, BOLD))
    else:
        print(
            c(
                f"  ⚠  Backfill complete — {grand_errors} error(s) encountered.",
                YELLOW,
                BOLD,
            )
        )
    print()
    if grand_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
