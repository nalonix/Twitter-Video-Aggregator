import pandas as pd
import uuid
from pathlib import Path

INPUT_FILE = Path("Cleaned.csv")
OUTPUT_FILE = Path("Cleaned.csv")

def assign_unique_ids(input_path, output_path):
    # Load CSV
    df = pd.read_csv(input_path)

    # Generate a unique ID for each row
    df["unique_id"] = [str(uuid.uuid4()) for _ in range(len(df))]

    # Optionally set as index
    df.set_index("unique_id", inplace=True)

    # Save to new CSV
    df.to_csv(output_path)

    print(f"✅ Assigned unique IDs and saved to {output_path}")
    print(f"Total entries: {len(df)}")

if __name__ == "__main__":
    assign_unique_ids(INPUT_FILE, OUTPUT_FILE)
