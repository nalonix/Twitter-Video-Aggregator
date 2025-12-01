import pandas as pd
import glob
import os
import re
from datetime import datetime, timedelta, timezone

INTERVAL = timedelta(minutes=5)

def _find_oldest_cleaned_file(directory: str) -> str | None:
    """
    Find the file with the largest leading number that matches the pattern:
    "[number] Old Cleaned.csv" in the given directory. Returns full path or None.
    """
    pattern = os.path.join(directory, "* Old Cleaned.csv")
    candidates = glob.glob(pattern)
    if not candidates:
        return None

    max_num = -1
    selected = None
    for path in candidates:
        name = os.path.basename(path)
        m = re.match(r"^\s*(\d+)\s+Old Cleaned\.csv$", name)
        if not m:
            continue
        num = int(m.group(1))
        if num > max_num:
            max_num = num
            selected = path
    return selected


def continue_timestamps(old_csv: str | None, new_csv: str, output_path: str):
    """
    Assign timestamps to a new CSV starting from the last timestamp of the old CSV,
    filling bottom → top (oldest at bottom, newest at top).

    If old_csv is None, automatically selects the file named "[largest number] Old Cleaned.csv"
    in the same directory as this script.
    """
    base_dir = os.path.dirname(__file__)
    # Auto-detect old_csv if not provided
    if not old_csv:
        old_csv = _find_oldest_cleaned_file(base_dir)
        if not old_csv:
            raise FileNotFoundError("No '* Old Cleaned.csv' files found to continue timestamps from.")
        print(f"🔎 Auto-detected oldest cleaned file: {os.path.basename(old_csv)}")
    else:
        # If a relative path provided, resolve relative to script dir
        if not os.path.isabs(old_csv):
            old_csv = os.path.join(base_dir, old_csv)

    df_old = pd.read_csv(old_csv) if os.path.exists(old_csv) else pd.DataFrame()
    df_new = pd.read_csv(new_csv)

    # Determine starting time
    if "fake_timestamp" in df_old.columns and not df_old.empty:
        try:
            last_ts = int(df_old["fake_timestamp"].iloc[-1])
            start_time = datetime.fromtimestamp(last_ts, tz=timezone.utc) + INTERVAL
        except Exception:
            start_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        start_time = datetime(1970, 1, 1, tzinfo=timezone.utc)

    # Reverse new CSV to fill bottom → top
    df_new_rev = df_new.iloc[::-1].reset_index(drop=True)
    timestamps = [(start_time + i * INTERVAL).timestamp() for i in range(len(df_new_rev))]
    df_new_rev["fake_timestamp"] = [int(ts) for ts in timestamps]
    df_new_rev["fake_date"] = df_new_rev["fake_timestamp"].apply(
        lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )

    # Revert to original top → bottom order
    df_final = df_new_rev.iloc[::-1].reset_index(drop=True)
    df_final.to_csv(output_path, index=False)
    print(f"✅ New CSV timestamps continued and saved to {output_path}")
    print(f"🕓 Bottom row: {df_final['fake_date'].iloc[-1]}, Top row: {df_final['fake_date'].iloc[0]}")


# Example usage
continue_timestamps("7 Old Cleaned.csv", "New Cleaned.csv", "New Cleaned.csv")
