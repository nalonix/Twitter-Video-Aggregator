import pandas as pd
import json
from pathlib import Path

CSV_FILE = "scrapped/Cleaned.csv"
STATE_FILE = "pagination_state.json"
MAX_RESULTS = 30

def load_state():
    if Path(STATE_FILE).exists() and Path(STATE_FILE).stat().st_size > 0:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {"last_id": None, "page_size": MAX_RESULTS}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

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
    state = load_state()

    # Ensure text column is always string
    if "text" in df.columns:
        df["text"] = df["text"].fillna("").astype(str)

    # Determine the rows to fetch
    if state["last_id"] is None:
        next_rows = df.head(max_results)
    else:
        last_index_list = df.index[df["unique_id"] == state["last_id"]].tolist()
        if not last_index_list:
            raise ValueError(f"Last ID {state['last_id']} not found in CSV")
        last_index = last_index_list[0]
        next_rows = df.iloc[last_index + 1 : last_index + 1 + max_results]

    if next_rows.empty:
        print("✅ No new entries to fetch.")
        return []

    # Normalize array-like columns
    array_columns = ["tags", "media_urls", "keywords"]
    for col in array_columns:
        if col in next_rows.columns:
            next_rows.loc[:, col] = next_rows[col].apply(normalize_column_as_list)

    # Update pagination state
    state["last_id"] = next_rows["unique_id"].iloc[-1]
    state["page_size"] = max_results
    save_state(state)

    # Return as Python list
    return next_rows.to_dict(orient="records")
