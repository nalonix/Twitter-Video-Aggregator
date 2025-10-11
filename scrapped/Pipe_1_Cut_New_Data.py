import pandas as pd

# File paths
file1_path = "New Data.csv"
file2_path = "Cleaned.csv"
output_path = "New Cleaned.csv"

# Load both CSVs
df1 = pd.read_csv(file1_path)
df2 = pd.read_csv(file2_path)

# Take the first 2 rows from file2
rows_to_find = df2.head(2)[["id", "created_at"]].reset_index(drop=True)

if len(rows_to_find) < 2:
    raise ValueError("⚠️ file2 must have at least two rows to compare.")

# Extract values for matching
first_id, first_created_at = rows_to_find.loc[0, ["id", "created_at"]]
second_id, second_created_at = rows_to_find.loc[1, ["id", "created_at"]]

# Find where the first row matches in file1
matches = df1[
    (df1["id"] == first_id) &
    (df1["created_at"] == first_created_at)
].index

if len(matches) == 0:
    raise ValueError("❌ First row from file2 not found in file1.")

# Check for consecutive second-row match
cut_index = None
for i in matches:
    if i + 1 < len(df1):
        next_row = df1.loc[i + 1]
        if (
            next_row["id"] == second_id and
            next_row["created_at"] == second_created_at
        ):
            cut_index = i + 1
            break

if cut_index is None:
    raise ValueError("❌ Could not find both rows consecutively in file1.")

# Slice file1 up to and including the second matching row
df_cut = df1.iloc[:cut_index + 1]

# Save the cut portion to a new CSV
df_cut.to_csv(output_path, index=False)

print(f"✅ Match found at index {cut_index-1}-{cut_index}.")
print(f"📁 New file saved as: {output_path}")
