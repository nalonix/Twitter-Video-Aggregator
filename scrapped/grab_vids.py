import pandas as pd
import json
from pathlib import Path

# Config
CSV_FILE = "scrapped/Cleaned.csv"
STATE_FILE = "pagination_state.json"
MAX_RESULTS = 30

def load_state():
    """Load pagination state from JSON, or initialize if not exists."""
    if Path(STATE_FILE).exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    else:
        return {"last_id": None, "page_size": MAX_RESULTS}

def save_state(state):
    """Save pagination state to JSON."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def grab_vids(max_results=MAX_RESULTS):
    """Fetch `max_results` entries from CSV based on last fetched unique ID."""
    df = pd.read_csv(CSV_FILE)
    state = load_state()
    
    if state["last_id"] is None:
        # Start from the top if no last_id
        next_rows = df.head(max_results)
    else:
        # Find the index of last fetched unique ID
        last_index_list = df.index[df["unique_id"] == state["last_id"]].tolist()
        if not last_index_list:
            raise ValueError(f"Last ID {state['last_id']} not found in CSV")
        last_index = last_index_list[0]
        next_rows = df.iloc[last_index + 1 : last_index + 1 + max_results]
    
    if next_rows.empty:
        print("✅ No new entries to fetch.")
        return pd.DataFrame()  # empty dataframe
    
    # Update the state with new last_id
    state["last_id"] = next_rows["unique_id"].iloc[-1]
    state["page_size"] = max_results
    save_state(state)
    
    return next_rows