import re
import sys

import pandas as pd
import spacy
import yake

print("🔄 Loading NLP models (spaCy + YAKE)...", flush=True)
nlp = spacy.load("en_core_web_sm")
yake_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)
print("✅ NLP models ready.", flush=True)


def extract_keywords(text: str, max_keywords: int = 8) -> str | None:
    """Extract concise keywords from text using spaCy and YAKE."""
    if not isinstance(text, str) or not text.strip():
        return None

    clean_text = re.sub(r"http\S+|https\S+|www\.\S+", "", text)

    doc = nlp(clean_text)
    spacy_candidates = {ent.text for ent in doc.ents if len(ent.text.split()) <= 3}
    spacy_candidates.update(
        token.text
        for token in doc
        if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2
    )

    yake_candidates = {kw for kw, _ in yake_extractor.extract_keywords(clean_text)}
    candidates = list(spacy_candidates.union(yake_candidates))

    seen = set()
    unique_keywords = []
    for kw in candidates:
        kw = kw.lower().strip()
        if kw and kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
        if len(unique_keywords) >= max_keywords:
            break

    return ", ".join(unique_keywords[:max_keywords]) if unique_keywords else None


input_file = "New Cleaned.csv"
output_file = "New Cleaned.csv"

print(f"📂 Loading {input_file} ...", flush=True)
df = pd.read_csv(input_file)
total_rows = len(df)

print(f"⚙️ Extracting keywords for {total_rows} rows...", flush=True)
keywords = []
for index, text in enumerate(df["text"], start=1):
    keywords.append(extract_keywords(text))
    if index == 1 or index % 10 == 0 or index == total_rows:
        print(f"   … {index}/{total_rows} rows processed", flush=True)

df["keywords"] = keywords
df.to_csv(output_file, index=False)
rows_with_keywords = df["keywords"].notna().sum()

print(f"✅ Keywords extracted for {rows_with_keywords} rows.", flush=True)
print(f"💾 Saved as {output_file}", flush=True)
