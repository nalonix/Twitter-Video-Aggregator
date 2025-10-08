import csv
import re

input_file = "EightK DB Main.csv"
output_file = "Cleaned.csv"

with open(input_file, newline='', encoding='utf-8') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + ['tags']  # add new column
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        video_url = row.get('video_url', '').strip()
        if not video_url:
            continue  # skip rows without video

        text = row.get('text', '')
        # extract hashtags using regex
        tags = re.findall(r"#(\w+)", text)
        row['tags'] = ','.join(tags)  # join tags as comma-separated string

        writer.writerow(row)

print(f"✅ Cleaned file saved as {output_file}")
