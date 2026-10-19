import re
import pandas as pd
import spacy

nlp = spacy.load("en_core_web_sm")

def generate_title(text: str, max_words: int = 8) -> str:
    """
    Generate a natural-sounding short title from text.
    - Removes hashtags, mentions, URLs.
    - Prioritizes proper nouns and named entities for natural readability.
    - Falls back gracefully for short or empty text.
    """
    # Ensure text is string
    if text is None or pd.isna(text):
        return "No title"
    text = str(text).strip()
    if not text:
        return "No title"

    # Clean text
    text = re.sub(r"http\S+|https\S+|www\.\S+", "", text)  # URLs
    text = re.sub(r"[@#]\S+", "", text)  # hashtags & mentions
    text = re.sub(r"\s+", " ", text).strip()  # extra spaces/newlines

    if not text:
        return "No title"

    doc = nlp(text)

    # Collect entities and proper nouns for importance
    important_words = []
    for ent in doc.ents:
        important_words.extend(ent.text.split())
    important_words.extend([token.text for token in doc if token.pos_ in ["PROPN", "NOUN"]])

    # Filter unique, preserve order
    seen = set()
    keywords = [w for w in important_words if (w.lower() not in seen and not seen.add(w.lower()))]

    # Build title using top keywords first
    if keywords:
        title_words = keywords[:max_words]
    else:
        # fallback: first max_words words from cleaned text
        title_words = text.split()[:max_words]

    title = " ".join(title_words)

    # Capitalize first letter
    title = title[0].upper() + title[1:]

    # Collapse multiple spaces
    title = re.sub(r"\s{2,}", " ", title)

    return title
