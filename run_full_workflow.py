"""
run_full_workflow.py — the one command for a full upload run. See WORKFLOW.md.

    python run_full_workflow.py [--no-fetch] [--skip-tags]

Retrying failed uploads is a separate command: python retry_failed.py
"""
import argparse
import csv
import html
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parent
SCRAPPED_DIR = ROOT / "scrapped"
REPORTS_DIR = ROOT / "reports"
NEW_DATA = SCRAPPED_DIR / "New Data.csv"
NEW_CLEANED = SCRAPPED_DIR / "New Cleaned.csv"
CLEANED = SCRAPPED_DIR / "Cleaned.csv"
FAILED_DIR = ROOT / "failed_uploads"

# Steps run with the project's venv (where mongoengine, telepot etc. live) even
# if this script was started with a different Python.
_VENV_PYTHON = ROOT / "venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

REQUIRED_COLUMNS = {
    "id",
    "video_url",
    "text",
    "unique_id",
    "keywords",
    "fake_timestamp",
    "fake_date",
}


def run_step(label: str, command: list[str], cwd: Path) -> tuple[int, str]:
    """Run a subprocess with live console output and captured logs."""
    print(f"\n{'=' * 60}", flush=True)
    print(f"▶ {label}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    log_lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log_lines.append(line)

    returncode = process.wait()
    return returncode, "".join(log_lines)


def rename_pipeline_output() -> None:
    if not NEW_CLEANED.exists():
        raise FileNotFoundError(
            f"Pipeline did not produce {NEW_CLEANED.name}. Cannot continue."
        )

    if CLEANED.exists():
        CLEANED.unlink()

    shutil.move(str(NEW_CLEANED), str(CLEANED))
    print(f"✅ Renamed {NEW_CLEANED.name} -> {CLEANED.name}", flush=True)


def validate_cleaned_csv() -> int:
    if not CLEANED.exists():
        raise FileNotFoundError(f"{CLEANED.name} not found after pipeline rename.")

    df = pd.read_csv(CLEANED)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Cleaned.csv is missing required columns from incomplete pipeline: {sorted(missing)}"
        )

    if df.empty:
        print("ℹ️ Cleaned.csv has no rows — upload step will be skipped.", flush=True)
        return 0

    print(f"✅ Cleaned.csv validated: {len(df)} rows ready for upload.", flush=True)
    return len(df)


def archive_cleaned_csv() -> Path:
    """Copy Cleaned.csv to the next "[N] Old Cleaned.csv" — the anchor for the next run's Pipe 1 & 7."""
    numbers = [
        int(m.group(1))
        for p in SCRAPPED_DIR.glob("* Old Cleaned.csv")
        if (m := re.match(r"^(\d+) Old Cleaned\.csv$", p.name))
    ]
    target = SCRAPPED_DIR / f"{max(numbers, default=0) + 1} Old Cleaned.csv"
    shutil.copy2(CLEANED, target)
    print(f"🗄️ Archived {CLEANED.name} -> {target.name}", flush=True)
    return target


def build_failure_html(rows: list[dict]) -> str:
    if not rows:
        return ""

    html_blocks = []
    for row in rows:
        user_display_name = (row.get("user_display_name") or "unknown").strip()
        description = (row.get("description") or "").strip()
        tweet_id = (row.get("tweet_id") or "").strip()
        post_link = (row.get("post_link") or "").strip()

        if not tweet_id and post_link:
            parts = post_link.rstrip("/").split("/")
            for part in reversed(parts):
                if part.isdigit():
                    tweet_id = part
                    break

        if not post_link and tweet_id:
            post_link = f"https://x.com/i/web/status/{tweet_id}"

        escaped_desc = html.escape(description or "No description")
        escaped_name = html.escape(user_display_name)

        # Standardize domain to twitter.com for robust widgets.js compatibility
        embed_link = post_link.replace("x.com", "twitter.com")
        escaped_embed_link = html.escape(embed_link)

        html_blocks.append(
            f"""
            <div class="report-card">
                <blockquote class="twitter-tweet" data-dnt="true" data-theme="dark">
                    <p lang="en" dir="ltr">{escaped_desc}</p>
                    &mdash; {escaped_name} (<a href="{escaped_embed_link}">View on X</a>)
                </blockquote>
            </div>
            """
        )

    return "\n".join(html_blocks)


def snapshot_failed_csvs() -> set[Path]:
    return set(FAILED_DIR.glob("*.csv")) if FAILED_DIR.exists() else set()


def new_failed_csv(before: set[Path], prefix: str) -> Path | None:
    """The CSV with `prefix` written since `before` was taken (i.e. by this run)."""
    created = sorted(p for p in snapshot_failed_csvs() - before if p.name.startswith(prefix))
    return created[-1] if created else None


def read_rows(path: Path | None) -> list[dict]:
    if not path:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_reports(
    run_dir: Path,
    run_stamp: str,
    logs: list[tuple[str, str]],
    row_count: int,
    failed_rows: list[dict],
    archived: Path | None,
    status: str,
) -> None:
    combined_logs = "\n".join(
        f"========== {label.upper()} ==========\n{log}" for label, log in logs
    )
    log_path = run_dir / "run_report.txt"
    log_path.write_text(combined_logs, encoding="utf-8")

    if failed_rows:
        failures_html = f'<div class="grid-embeds">{build_failure_html(failed_rows)}</div>'
    else:
        failures_html = '<p style="color: var(--text-secondary); font-style: italic;">No failed uploads in this run.</p>'

    html_report = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Workflow Run Report</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #0b0f19;
                --card-bg: rgba(30, 41, 59, 0.4);
                --card-border: rgba(255, 255, 255, 0.08);
                --text-primary: #f8fafc;
                --text-secondary: #94a3b8;
                --accent-primary: #6366f1;
                --accent-secondary: #06b6d4;
                --success: #10b981;
                --danger: #ef4444;
            }}
            body {{
                font-family: 'Inter', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-primary);
                margin: 0;
                padding: 40px 20px;
                min-height: 100vh;
                line-height: 1.5;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
            }}
            header {{
                margin-bottom: 40px;
                border-bottom: 1px solid var(--card-border);
                padding-bottom: 24px;
            }}
            h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                margin: 0 0 12px 0;
                background: linear-gradient(135deg, var(--accent-secondary) 0%, var(--accent-primary) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .meta-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin-bottom: 32px;
            }}
            .meta-card {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                backdrop-filter: blur(12px);
                padding: 16px 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            }}
            .meta-label {{
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: var(--text-secondary);
                margin-bottom: 4px;
            }}
            .meta-value {{
                font-size: 1.125rem;
                font-weight: 600;
                color: var(--text-primary);
            }}
            .meta-value.success {{
                color: var(--success);
            }}
            .meta-value.danger {{
                color: var(--danger);
            }}
            section {{
                margin-bottom: 48px;
            }}
            h2 {{
                font-size: 1.5rem;
                font-weight: 600;
                margin-top: 0;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 8px;
                border-bottom: 1px solid var(--card-border);
                padding-bottom: 8px;
            }}
            .grid-embeds {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 24px;
            }}
            @media (min-width: 768px) {{
                .grid-embeds {{
                    grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
                }}
            }}
            .report-card {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                backdrop-filter: blur(12px);
                border-radius: 16px;
                padding: 16px;
                display: flex;
                flex-direction: column;
                align-items: center;
                transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
            }}
            .report-card:hover {{
                transform: translateY(-4px);
                border-color: rgba(99, 102, 241, 0.3);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
            }}
            .report-card .twitter-tweet {{
                margin: 0 !important;
                width: 100% !important;
            }}
            .console-box {{
                background: #060913;
                border: 1px solid var(--card-border);
                border-radius: 12px;
                padding: 20px;
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
            }}
            pre {{
                margin: 0;
                font-family: 'Courier New', Courier, monospace;
                font-size: 0.875rem;
                color: #a7f3d0;
                overflow-x: auto;
                white-space: pre-wrap;
                word-break: break-all;
                max-height: 400px;
                overflow-y: auto;
            }}
        </style>
        <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Workflow Run Report</h1>
            </header>

            <div class="meta-grid">
                <div class="meta-card">
                    <div class="meta-label">Timestamp</div>
                    <div class="meta-value">{run_stamp}</div>
                </div>
                <div class="meta-card">
                    <div class="meta-label">Status</div>
                    <div class="meta-value {'success' if status == 'completed' else 'danger'}">{html.escape(status)}</div>
                </div>
                <div class="meta-card">
                    <div class="meta-label">Rows Processed</div>
                    <div class="meta-value">{row_count}</div>
                </div>
                <div class="meta-card">
                    <div class="meta-label">Failed Uploads</div>
                    <div class="meta-value {'danger' if failed_rows else 'success'}">{len(failed_rows)}</div>
                </div>
                <div class="meta-card">
                    <div class="meta-label">Archived As</div>
                    <div class="meta-value">{html.escape(archived.name) if archived else "—"}</div>
                </div>
            </div>

            <section>
                <h2>Failed uploads</h2>
                {failures_html}
            </section>

            <section>
                <h2>Run logs</h2>
                <div class="console-box">
                    <pre>{html.escape(combined_logs)}</pre>
                </div>
            </section>
        </div>
    </body>
    </html>
    """
    html_path = run_dir / "run_report.html"
    html_path.write_text(html_report, encoding="utf-8")

    print(f"\n📄 Run report saved to {log_path}", flush=True)
    print(f"📄 HTML report saved to {html_path}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch likes → pipeline → upload → archive → backfill → tag stats")
    parser.add_argument(
        "--no-fetch", action="store_true", help="use the existing scrapped/New Data.csv instead of fetching likes from X"
    )
    parser.add_argument("--skip-tags", action="store_true", help="don't recalculate tag stats/relationships")
    args = parser.parse_args()

    if args.no_fetch and not NEW_DATA.exists():
        raise SystemExit(f"❌ {NEW_DATA} not found. Export your likes to it first, or drop --no-fetch.")

    REPORTS_DIR.mkdir(exist_ok=True)
    run_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = REPORTS_DIR / f"run_{run_stamp}"
    run_dir.mkdir(exist_ok=True)

    py = [PYTHON, "-u"]
    print(f"🐍 Using {PYTHON}", flush=True)
    logs: list[tuple[str, str]] = []
    row_count = 0
    failed_rows: list[dict] = []
    archived: Path | None = None
    warnings: list[str] = []

    def abort(message: str) -> None:
        write_reports(run_dir, run_stamp, logs, row_count, failed_rows, archived, "failed")
        raise SystemExit(f"\n❌ {message}")

    print("⚙️ Running full workflow...\n", flush=True)

    # ── 0. Fetch likes from X: → New Data.csv ───────────────────────────────────
    if not args.no_fetch:
        code, log = run_step("Step 0/5 — Fetch likes from X (fetch/fetch_likes.py)", py + ["-m", "fetch.fetch_likes"], ROOT)
        logs.append(("fetch", log))
        if code != 0:
            abort(f"Fetching likes failed with exit code {code}. Fix it, or run with --no-fetch to use the existing New Data.csv.")
    else:
        print("\n⏭ Step 0/5 — Fetch skipped (--no-fetch); using the existing New Data.csv.", flush=True)

    # ── 1. Data pipeline: New Data.csv → Cleaned.csv ────────────────────────────
    code, log = run_step(
        "Step 1/5 — Data pipeline (pipeline/run_all_pipes.py)",
        py + [str(ROOT / "pipeline" / "run_all_pipes.py"), str(SCRAPPED_DIR)],
        ROOT,
    )
    logs.append(("pipeline", log))
    if code != 0:
        abort(f"Pipeline failed with exit code {code}.")

    rename_pipeline_output()
    row_count = validate_cleaned_csv()

    if row_count == 0:
        print("\n⏭ Nothing new to upload — skipping remaining steps.", flush=True)
        logs.append(("upload", "(skipped — no rows to upload)"))
        write_reports(run_dir, run_stamp, logs, row_count, failed_rows, archived, "completed")
        raise SystemExit(0)

    # ── 2. Upload to Telegram + log to MongoDB ──────────────────────────────────
    before_upload = snapshot_failed_csvs()
    code, log = run_step("Step 2/5 — Upload videos (upload/upload_videos.py)", py + ["-m", "upload.upload_videos"], ROOT)
    logs.append(("upload", log))
    if code != 0:
        abort(
            f"Upload failed with exit code {code}. Cleaned.csv was NOT archived — "
            "check which videos were already posted before re-running."
        )

    failed_csv = new_failed_csv(before_upload, "failed_uploads_")
    failed_rows = read_rows(failed_csv)
    if failed_csv:
        shutil.copy2(failed_csv, run_dir / failed_csv.name)

    # Archive now: these rows are posted, so the next run must cut against them.
    archived = archive_cleaned_csv()

    # ── 3. Backfill video_url / display name for this batch ─────────────────────
    code, log = run_step(
        "Step 3/5 — Backfill video URLs (maintenance/back_fill_url.py)",
        py + ["-m", "maintenance.back_fill_url", str(CLEANED)],
        ROOT,
    )
    logs.append(("backfill", log))
    if code != 0:
        warnings.append(f"backfill exited with code {code}")

    # ── 4. Refresh tag stats + related tags ─────────────────────────────────────
    if not args.skip_tags:
        for label, module in (
            ("Step 4/5 — Tag stats (maintenance/tag_stats.py)", "maintenance.tag_stats"),
            ("Step 5/5 — Tag relationships (maintenance/tag_relationships.py)", "maintenance.tag_relationships"),
        ):
            code, log = run_step(label, py + ["-m", module], ROOT)
            logs.append((module.split(".")[-1], log))
            if code != 0:
                warnings.append(f"{module} exited with code {code}")
    else:
        print("\n⏭ Steps 4-5 — Tag refresh skipped (--skip-tags).", flush=True)

    status = "completed" if not warnings else "completed with warnings: " + "; ".join(warnings)
    write_reports(run_dir, run_stamp, logs, row_count, failed_rows, archived, status)
    print(f"\n{'✅' if not warnings else '⚠️'} Full workflow {status}.", flush=True)
    if failed_csv:
        print(
            f"🔁 {len(failed_rows)} upload(s) failed. Retry them with: "
            f'python retry_failed.py "{failed_csv.relative_to(ROOT)}"',
            flush=True,
        )
