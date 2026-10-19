import os

import pandas as pd
from common import find_latest_old_cleaned

# File paths
file1_path = "New Data.csv"
output_path = "New Cleaned.csv"

file2_path = find_latest_old_cleaned()
if not file2_path:
    raise FileNotFoundError(
        "No '* Old Cleaned.csv' files found in the scrapped directory."
    )
print(f"🔎 Auto-detected latest cleaned file: {os.path.basename(file2_path)}")

# Load both CSVs
df1 = pd.read_csv(file1_path)
df2 = pd.read_csv(file2_path)

# Take the first 5 rows (newest) from the last uploaded batch 🤖
rows_to_find = df2.head(5)[["id", "created_at"]].reset_index(drop=True)

print("Rows to find:", rows_to_find)

if len(rows_to_find) < 5:
    raise ValueError("⚠️ file2 must have at least 5 rows to compare.")


matches = []
for idx, row in rows_to_find.iterrows():
    print(f"Looking for row {idx + 1}: id={row['id']}, created_at={row['created_at']}")
    matched_entry = df1.index[
        (df1["id"] == row["id"]) & (df1["created_at"] == row["created_at"])
    ].tolist()
    matches.append(matched_entry[0] if matched_entry else None)


# Allow at most one of the 5 anchor rows to be missing (e.g. a deleted post) 🤖
if matches.count(None) > 1:
    raise ValueError("❌ Less than 4 of 5 anchor rows found in New Data.csv.")

# Verify that matches are close together (verifying integrity)
# Distribution can't be more than 5 (first fetched number of rows) 🤖
distribution = max(filter(lambda x: x is not None, matches)) - min(
    filter(lambda x: x is not None, matches)
)
if distribution > 5:
    raise ValueError("❌ Matches found are too far apart, data integrity check failed.")

print("Matches found:", matches)

cut_index = min(filter(lambda x: x is not None, matches))

print(f"✂️ Cutting file1 up to index {cut_index}")

# Keep only the rows above the first match (the new likes)
df_cut = df1.iloc[:cut_index]

# Save the cut portion to a new CSV
df_cut.to_csv(output_path, index=False)

print(f"📁 New file saved as: {output_path}")
