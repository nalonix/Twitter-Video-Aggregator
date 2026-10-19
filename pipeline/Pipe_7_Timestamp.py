import pandas as pd
import os
from datetime import datetime, timedelta, timezone

from common import find_latest_old_cleaned

INTERVAL = timedelta(minutes=5)

def continue_timestamps(old_csv: str | None, new_csv: str, output_path: str):
    """
    Assign timestamps to a new CSV starting from the last timestamp of the old CSV,
    filling bottom → top (oldest at bottom, newest at top).

    If old_csv is None, automatically selects the file named "[largest number] Old Cleaned.csv"
    in the current (data) directory.
    """
    if not old_csv:
        old_csv = find_latest_old_cleaned()
        if not old_csv:
            raise FileNotFoundError("No '* Old Cleaned.csv' files found to continue timestamps from.")
        print(f"🔎 Auto-detected latest cleaned file: {os.path.basename(old_csv)}")

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


if __name__ == "__main__":
    continue_timestamps(None, "New Cleaned.csv", "New Cleaned.csv")

