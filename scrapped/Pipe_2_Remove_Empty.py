import pandas as pd
import os

# File paths
input_file = "New Cleaned.csv"
cleaned_output_file = "New Cleaned.csv"
empty_dump_file = "empty_url_dump.csv"

# --------------------------
# 1️⃣ Load new CSV
# --------------------------
df = pd.read_csv(input_file)

# Identify empty or missing URLs in the new input file
is_empty = df["video_url"].isna() | (df["video_url"].astype(str).str.strip() == "")
new_empty_df = df[is_empty]      # rows with empty URLs
df_valid = df[~is_empty]         # rows with valid URLs

# --------------------------
# 2️⃣ Load previous empty dump (if it exists)
# --------------------------
if os.path.exists(empty_dump_file):
    old_empty_df = pd.read_csv(empty_dump_file)
else:
    old_empty_df = pd.DataFrame(columns=df.columns)

# --------------------------
# 3️⃣ Combine old + new empty rows (unique by id)
# --------------------------
combined_empty_df = (
    pd.concat([old_empty_df, new_empty_df])
    .drop_duplicates(subset=["id"])
)

# Save updated empty dump
combined_empty_df.to_csv(empty_dump_file, index=False)

# --------------------------
# 4️⃣ Ignore all rows in cleaned data if their id is in empty dump
# --------------------------
empty_ids = set(combined_empty_df["id"])

df_valid = df_valid[~df_valid["id"].isin(empty_ids)]

# --------------------------
# 5️⃣ Keep only unique ids in cleaned data
# --------------------------
df_valid = df_valid.drop_duplicates(subset=["id"])

# --------------------------
# 6️⃣ Trim columns up to conversation_id_str
# --------------------------
if "conversation_id_str" not in df_valid.columns:
    raise ValueError("❌ 'conversation_id_str' column not found in CSV.")

cut_index = df_valid.columns.get_loc("conversation_id_str")
df_valid = df_valid.iloc[:, :cut_index + 1]

# --------------------------
# 7️⃣ Save cleaned file
# --------------------------
df_valid.to_csv(cleaned_output_file, index=False)

print("✅ Cleaned file updated and saved.")
print("📥 Empty URLs appended to empty_url_dump.csv (unique by id).")
print("🧹 Cleaned data only contains unique ids.")
print("🚫 Any id that ever appeared in empty dump is now permanently ignored.")
