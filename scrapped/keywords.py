import pandas as pd
import spacy
from keybert import KeyBERT
import yake

# Load your CSV
df = pd.read_csv("Cleaned.csv")

# Initialize spaCy and KeyBERT
nlp = spacy.load("en_core_web_sm")  # You can use 'en_core_web_lg' for heavier embeddings
kw_model = KeyBERT()

# YAKE setup
yake_kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)  # up to 2-grams, top 10 candidate phrases

def extract_keywords_heavy(text):
    if pd.isna(text) or not text.strip():
        return ""
    
    # --- spaCy entities and nouns ---
    doc = nlp(text)
    spacy_keywords = {ent.text.lower() for ent in doc.ents}
    spacy_keywords.update({token.text.lower() for token in doc if token.pos_ in ["NOUN", "PROPN"]})
    
    # --- YAKE keywords ---
    yake_candidates = [kw.lower() for kw, score in yake_kw_extractor.extract_keywords(text)]
    
    # Combine spaCy + YAKE candidates
    combined_candidates = list(spacy_keywords.union(yake_candidates))
    
    # --- KeyBERT refinement ---
    if combined_candidates:
        keybert_keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1,2),
            stop_words='english',
            top_n=4,
            candidates=combined_candidates  # restrict to combined candidates
        )
        return ", ".join([kw for kw, _ in keybert_keywords])
    else:
        return ""

# Apply function with console logging every 100 rows
for idx, row in df.iterrows():
    df.at[idx, "keywords"] = extract_keywords_heavy(row["text"])
    if (idx + 1) % 100 == 0:
        print(f"✅ Processed {idx + 1} rows")

# Save results
df.to_csv("with_heavy_keywords.csv", index=False)
print("✅ Heavy NLP keywords generated and saved to with_heavy_keywords.csv")
