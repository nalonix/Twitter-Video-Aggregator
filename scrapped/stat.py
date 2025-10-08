import pandas as pd

# Load the cleaned CSV
df = pd.read_csv("Cleaned.csv")

# Drop rows missing video_url or duration (if any slipped through)
df = df.dropna(subset=["video_url", "video_duration"])

# --- 1️⃣ Top 5 most common tags ---
all_tags = df["tags"].dropna().str.split(",").explode().str.strip().str.lower()
top_tags = all_tags.value_counts().head(5)

# --- 2️⃣ How many posts have at least one tag ---
tagged_posts = df["tags"].notna().sum()

# --- 3️⃣ Top 5 most common usernames ---
top_users = df["username"].value_counts().head(5)

# --- 4️⃣ Average, longest, and shortest video durations ---
avg_duration = df["video_duration"].mean()
longest = df.loc[df["video_duration"].idxmax()]
shortest = df.loc[df["video_duration"].idxmin()]

# --- Print results ---
print("📊 Top 5 Common Tags:")
print(top_tags, "\n")

print(f"🏷️ Posts with at least one tag: {tagged_posts}\n")

print("👤 Top 5 Common Usernames:")
print(top_users, "\n")

print(f"⏱️ Average Duration: {avg_duration:.2f} seconds")
print(f"🏁 Longest Duration: {longest['video_duration']} seconds (Tweet ID: {longest['id']})")
print(f"⚡ Shortest Duration: {shortest['video_duration']} seconds (Tweet ID: {shortest['id']})")

