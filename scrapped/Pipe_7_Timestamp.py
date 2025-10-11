import pandas as pd
from datetime import datetime, timedelta, timezone

INTERVAL = timedelta(minutes=5)

def continue_timestamps(old_csv, new_csv, output_path):
    """
    Assign timestamps to a new CSV starting from the last timestamp of the old CSV,
    filling bottom → top (oldest at bottom, newest at top).
    """
    df_old = pd.read_csv(old_csv)
    df_new = pd.read_csv(new_csv)

    # Determine starting time
    if "fake_timestamp" in df_old.columns and not df_old.empty:
        last_ts = int(df_old["fake_timestamp"].iloc[-1])
        start_time = datetime.fromtimestamp(last_ts, tz=timezone.utc) + INTERVAL
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
continue_timestamps("Cleaned.csv", "New Cleaned.csv", "New Cleaned.csv")
