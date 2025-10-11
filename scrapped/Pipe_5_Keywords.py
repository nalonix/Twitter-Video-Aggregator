import pandas as pd
import re
import spacy
from keybert import KeyBERT
import yake

# --- Load NLP models ---
print("🔄 Loading NLP models...")
nlp = spacy.load("en_core_web_sm")
kw_model = KeyBERT()
yake_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)

def extract_keywords(text: str, max_keywords: int = 8) -> str:
    """
    Extract concise, meaningful keywords from a text using spaCy, YAKE, and KeyBERT.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    # 1️⃣ Clean text
    clean_text = re.sub(r"http\S+|https\S+|www\.\S+", "", text)

    # 2️⃣ Extract initial candidates with spaCy (entities + nouns)
    doc = nlp(clean_text)
    spacy_candidates = {ent.text for ent in doc.ents if len(ent.text.split()) <= 3}
    spacy_candidates.update({
        token.text for token in doc
        if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2
    })

    # 3️⃣ Add YAKE candidates
    yake_candidates = {kw for kw, score in yake_extractor.extract_keywords(clean_text)}

    # Combine
    candidates = list(spacy_candidates.union(yake_candidates))

    # 4️⃣ Use KeyBERT to rank keywords
    try:
        keybert_keywords = kw_model.extract_keywords(
            clean_text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=max_keywords,
            candidates=candidates if candidates else None
        )
    except Exception:
        keybert_keywords = []

    # 5️⃣ Finalize output
    keywords = [kw for kw, _ in keybert_keywords]
    if not keywords:
        keywords = list(yake_candidates)[:max_keywords]

    # Deduplicate + lowercase
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw = kw.lower()
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return ", ".join(unique_keywords[:max_keywords]) if unique_keywords else None

# --- Process CSV ---
input_file = "New Cleaned.csv"
output_file = "New Cleaned.csv"

print(f"📂 Loading {input_file} ...")
df = pd.read_csv(input_file)

# Apply keyword extraction
print("⚙️ Extracting keywords...")
df["keywords"] = df["text"].apply(extract_keywords)

# Save results
df.to_csv(output_file, index=False)
rows_with_keywords = df["keywords"].notna().sum()

print(f"✅ Keywords extracted for {rows_with_keywords} rows.")
print(f"💾 Saved as {output_file}")
