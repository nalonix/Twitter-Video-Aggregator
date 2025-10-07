import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

def generate_title(text: str, sentences_count: int = 1) -> str:
    """
    Summarize text into a short title-like string, removing links.
    
    Args:
        text (str): Input text (tweet, article, etc.)
        sentences_count (int): How many sentences to include in the summary
    
    Returns:
        str: Summarized text
    """
    # Remove URLs
    clean_text = re.sub(r"http\S+|https\S+|www\.\S+", "", text)

    parser = PlaintextParser.from_string(clean_text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    summary_sentences = summarizer(parser.document, sentences_count)
    
    # Join sentences back into a single string
    summary = " ".join([str(s) for s in summary_sentences]).strip()
    return summary
