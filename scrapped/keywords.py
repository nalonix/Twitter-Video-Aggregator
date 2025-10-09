import re
import spacy
from keybert import KeyBERT
import yake

# Load NLP models
nlp = spacy.load("en_core_web_sm")  # you can use 'en_core_web_lg' for better embeddings
kw_model = KeyBERT()
yake_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)  # up to 2-grams

def generate_title_heavy(text: str, max_keywords: int = 3) -> str:
    """
    Generate a short, title-like summary from a text using spaCy, YAKE, and KeyBERT.
    
    Args:
        text (str): Input text
        max_keywords (int): Max number of keywords/phrases to include in title
    
    Returns:
        str: Generated title
    """
    if not text or not text.strip():
        return "No title"

    # Remove URLs
    clean_text = re.sub(r"http\S+|https\S+|www\.\S+", "", text)

    # --- Extract candidates ---
    doc = nlp(clean_text)
    
    # spaCy entities and important nouns
    spacy_keywords = {ent.text for ent in doc.ents if len(ent.text.split()) <= 3}
    spacy_keywords.update({token.text for token in doc if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2})

    # YAKE keywords
    yake_candidates = {kw for kw, score in yake_extractor.extract_keywords(clean_text)}

    # Combine candidates
    candidates = list(spacy_keywords.union(yake_candidates))
    
    if not candidates:
        # fallback: just take first few words
        return " ".join(clean_text.strip().split()[:5])

    # KeyBERT ranking
    keybert_keywords = kw_model.extract_keywords(
        clean_text,
        keyphrase_ngram_range=(1,2),
        stop_words='english',
        top_n=max_keywords,
        candidates=candidates
    )

    title = " | ".join([kw for kw, _ in keybert_keywords])
    
    # fallback if KeyBERT returns empty
    if not title:
        title = " ".join(clean_text.strip().split()[:5])
    
    return title
