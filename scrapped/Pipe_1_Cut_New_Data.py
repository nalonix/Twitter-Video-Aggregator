import pandas as pd

# File paths
file1_path = "New Data.csv"
file2_path = "7 Old Cleaned.csv"
output_path = "New Cleaned.csv"

# Load both CSVs
df1 = pd.read_csv(file1_path)
df2 = pd.read_csv(file2_path)

# Take the first 2 rows from file2 🤖
rows_to_find = df2.head(5)[["id", "created_at"]].reset_index(drop=True)

print("Rows to find:", rows_to_find)

if len(rows_to_find) < 5:
    raise ValueError("⚠️ file2 must have at least 5 rows to compare.")

matches = []
# Extract values for matching
first_id, first_created_at = rows_to_find.loc[0, ["id", "created_at"]]
second_id, second_created_at = rows_to_find.loc[1, ["id", "created_at"]]

for idx, row in rows_to_find.iterrows():
    print(f"Looking for row {idx + 1}: id={row['id']}, created_at={row['created_at']}")
    matched_entry = df1.index[(df1["id"] == row["id"]) & (df1["created_at"] == row["created_at"])].tolist()
    matches.append(matched_entry[0] if matched_entry else None)
    
    
# Check there's at least 3 matches 🤖
if matches.count(None) > 2:
    raise ValueError("❌ Less than 3 matches found between the two files.")

# Verify that matches are close together (verifying integrity)
# Distribution can't be more than 5 (first fetched number of rows) 🤖
distribution = max(filter(lambda x: x is not None, matches)) - min(filter(lambda x: x is not None, matches))
if distribution > 5:
    raise ValueError("❌ Matches found are too far apart, data integrity check failed.")

print("Matches found:", matches)

cut_index = min(filter(lambda x: x is not None, matches))

print(f"✂️ Cutting file1 up to index {cut_index}")

# Slice file1 up to and including the later of the two matches
df_cut = df1.iloc[:cut_index]

# Save the cut portion to a new CSV
df_cut.to_csv(output_path, index=False)

print(f"📁 New file saved as: {output_path}")
