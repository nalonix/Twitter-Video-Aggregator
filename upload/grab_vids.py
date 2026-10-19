import json
from pathlib import Path

import pandas as pd

CSV_FILE = Path(__file__).resolve().parent.parent / "scrapped" / "Cleaned.csv"
MAX_RESULTS = 30

def normalize_column_as_list(x):
    if pd.isna(x):
        return []
    x_str = str(x).strip()
    if x_str == "":
        return []
    try:
        val = json.loads(x_str)
        if isinstance(val, list):
            return [str(k).strip() for k in val if str(k).strip()]
    except Exception:
        pass
    return [k.strip() for k in x_str.split(",") if k.strip()]

def grab_vids(max_results=MAX_RESULTS):
    df = pd.read_csv(CSV_FILE)

    if "text" in df.columns:
        df["text"] = df["text"].fillna("").astype(str)

    if max_results is None:
        next_rows = df
    else:
        next_rows = df.head(max_results)

    if next_rows.empty:
        print("✅ No new entries to fetch.")
        return []

    array_columns = ["tags", "media_urls", "keywords"]
    for col in array_columns:
        if col in next_rows.columns:
            next_rows.loc[:, col] = next_rows[col].apply(normalize_column_as_list)

    return next_rows.to_dict(orient="records")
