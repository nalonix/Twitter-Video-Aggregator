import pandas as pd
import re

# Input and output file paths
input_file = "New Cleaned.csv"
output_file = input_file  # overwrite the same file

# Load the CSV
df = pd.read_csv(input_file)

# --- Extract tags function ---
def extract_unique_tags(text):
    if not isinstance(text, str):
        return None
    # Find hashtags (letters, numbers, underscore after #)
    tags = re.findall(r"#(\w+)", text)
    # Normalize: lowercase + unique while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag_lower)
    return ",".join(unique_tags) if unique_tags else None

# Apply extraction
df["tags"] = df["text"].apply(extract_unique_tags)

# Save the new CSV
df.to_csv(output_file, index=False)

# Count how many rows have tags
rows_with_tags = df["tags"].notna().sum()

print(f"✅ Tags extracted and saved to {output_file}")
print(f"🏷️ {rows_with_tags} rows contain hashtags.")
