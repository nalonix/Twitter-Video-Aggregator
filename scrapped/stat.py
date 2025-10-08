import csv

# Path to your CSV file
csv_file = "EightK DB Main.csv"

# Column to check
column_name = "video_url"

blank_count = 0
total_rows = 0

with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        if not row[column_name].strip():
            blank_count += 1

print(f"Total rows: {total_rows}")
print(f"Rows with blank '{column_name}': {blank_count}")
print(f"Percentage blank: {blank_count / total_rows * 100:.2f}%")
