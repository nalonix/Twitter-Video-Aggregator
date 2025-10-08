import pandas as pd
from datetime import datetime, timedelta, timezone

INTERVAL = timedelta(minutes=5)

def assign_from_unix_start(csv_path, output_path):
    """Assigns timestamps starting from UNIX epoch (1970-01-01)."""
    df = pd.read_csv(csv_path)

    start_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
    timestamps = []
    for i in range(len(df)):
        ts = start_time + i * INTERVAL
        timestamps.append(int(ts.timestamp()))

    df["fake_timestamp"] = timestamps
    df["fake_date"] = df["fake_timestamp"].apply(
        lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )

    df.to_csv(output_path, index=False)
    print(f"✅ Assigned timestamps from UNIX start to {len(df)} rows.")
    print(f"📁 Saved updated data to {output_path}")
    print(f"🕓 Last assigned date: {df['fake_date'].iloc[-1]}")


def assign_from_last_entry(old_path, new_path, output_path):
    """Assigns timestamps to new data starting from the last entry in the old CSV."""
    df_old = pd.read_csv(old_path)
    df_new = pd.read_csv(new_path)

    if "fake_timestamp" in df_old.columns and not df_old.empty:
        last_ts = int(df_old["fake_timestamp"].iloc[-1])
        base_time = datetime.fromtimestamp(last_ts, tz=timezone.utc) + INTERVAL
    else:
        base_time = datetime(1970, 1, 1, tzinfo=timezone.utc)

    timestamps = []
    for i in range(len(df_new)):
        ts = base_time + i * INTERVAL
        timestamps.append(int(ts.timestamp()))

    df_new["fake_timestamp"] = timestamps
    df_new["fake_date"] = df_new["fake_timestamp"].apply(
        lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )

    df_new.to_csv(output_path, index=False)
    print(f"✅ Assigned timestamps (resumed) to {len(df_new)} new rows.")
    print(f"📁 Saved updated data to {output_path}")
    print(f"🕓 Last assigned date: {df_new['fake_date'].iloc[-1]}")


# Example usage:
assign_from_unix_start("Cleaned.csv", "Cleaned.csv")
# assign_from_last_entry("Cleaned.csv", "NewData.csv", "NewData_updated.csv")
