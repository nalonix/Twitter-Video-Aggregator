import pandas as pd

# Input and output file paths
input_file = "New Cleaned.csv"
output_file = "New Cleaned.csv"

# Load the CSV
df = pd.read_csv(input_file)

# 1️⃣ Remove rows with missing or empty video_url
df = df[df["video_url"].notna()]                # drop NaN
df = df[df["video_url"].astype(str).str.strip() != ""]  # drop empty strings

# 2️⃣ Keep only columns up to 'conversation_id_str'
if "conversation_id_str" not in df.columns:
    raise ValueError("❌ 'conversation_id_str' column not found in CSV.")

# Find index of that column and slice
cut_index = df.columns.get_loc("conversation_id_str")
df = df.iloc[:, :cut_index + 1]  # include that column

# 3️⃣ Save cleaned data
df.to_csv(output_file, index=False)

print(f"✅ Cleaned file saved as {output_file}")
print(f"🧹 Rows with empty 'video_url' removed, columns trimmed up to 'conversation_id_str'.")
