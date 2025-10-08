import pandas as pd
import re

# Load the original CSV
df = pd.read_csv("Cleaned.csv")

# Remove rows without video URLs
df = df.dropna(subset=["video_url"])

# --- Create lowercase tags column ---
def extract_tags(text):
    if not isinstance(text, str):
        return None
    tags = re.findall(r"#(\w+)", text)
    return ",".join(t.lower() for t in tags) if tags else None

df["tags"] = df["text"].apply(extract_tags)

# Save the updated CSV
df.to_csv("Cleaned.csv", index=False)

print("✅ Cleaned_with_tags.csv created with lowercase tags.")
