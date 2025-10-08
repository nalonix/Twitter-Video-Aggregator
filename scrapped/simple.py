import pandas as pd

# Load CSV
df = pd.read_csv("Cleaned.csv")

# Count entries
num_entries = len(df)
print(f"Number of entries: {num_entries}")
