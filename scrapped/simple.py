import pandas as pd

# Load CSV
df = pd.read_csv("New Cleaned.csv")

# Count entries
num_entries = len(df)
print(f"Number of entries: {num_entries}")
