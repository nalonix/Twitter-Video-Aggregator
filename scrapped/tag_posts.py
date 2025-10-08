import pandas as pd

# Load your cleaned CSV
df = pd.read_csv("Cleaned.csv")

# Ensure tags column exists
if "tags" not in df.columns:
    raise ValueError("The 'tags' column was not found in Cleaned.csv")

def remove_duplicates(tags_str):
    if pd.isna(tags_str):
        return ""
    tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
    unique_tags = sorted(set(tags))  # sorted for consistency
    return ",".join(unique_tags)

# Apply the function
df["tags"] = df["tags"].apply(remove_duplicates)

# Save to new file
df.to_csv("Cleaned.csv", index=False)

print("✅ Duplicate tags removed and saved to 'Cleaned_NoDupes.csv'")
