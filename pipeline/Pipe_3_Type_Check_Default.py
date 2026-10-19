import pandas as pd

# Input and output file paths
input_file = "New Cleaned.csv"
output_file = "New Cleaned.csv"

# Load CSV
df = pd.read_csv(input_file)

# Columns to fix
count_columns = [
    "retweet_count",
    "favorite_count",
    "reply_count",
    "quote_count",
    "bookmark_count",
    "view_count"
]

# Keep track of how many rows were changed
affected_rows = set()

for col in count_columns:
    if col not in df.columns:
        print(f"⚠️ Column '{col}' not found — skipping.")
        continue

    # Convert to numeric, forcing errors to NaN
    before_invalid = df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum()
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Track affected rows (where conversion changed value or was NaN/empty)
    invalid_indices = df[df[col] == 0].index
    affected_rows.update(invalid_indices)

# Save updated CSV
df.to_csv(output_file, index=False)

print(f"✅ Cleaned file saved as {output_file}")
print(f"🧮 {len(affected_rows)} rows had invalid or empty counts replaced with 0.")
