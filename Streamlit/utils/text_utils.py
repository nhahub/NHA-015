"""
Text processing and NLP utilities
"""
import re
from collections import Counter
import pandas as pd


def get_stopwords():
    """Return set of common stopwords in English and Arabic"""
    return {
        # English stopwords
        'the', 'and', 'in', 'of', 'to', 'a', 'is', 'for', 'on', 'with', 
        'at', 'by', 'from', 'it', 'as', 'an', 'that',
        # Arabic stopwords
        'في', 'من', 'على', 'إلى', 'عن', 'مع', 'هذا', 'هذه', 
        'أن', 'كان', 'ما', 'لا', 'لم', 'التي', 'الذي', 'بين',
        # Common news terms
        'news', 'report', 'daily', 'update', 'latest', 'breaking', 
        'today', 'year', 'after', 'before', 'when', 'where'
    }


def get_top_keywords(texts, top_n=15):
    """
    Extract top keywords from text list
    Args:
        texts: List of text strings
        top_n: Number of top keywords to return
    Returns:
        DataFrame with keywords and counts
    """
    if not texts:
        return pd.DataFrame()
    
    stopwords = get_stopwords()
    all_text = " ".join([str(t) for t in texts]).lower()
    words = re.findall(r'\w+', all_text)
    
    # Filter words
    filtered = [
        w for w in words 
        if len(w) > 3 and w not in stopwords and not w.isdigit()
    ]
    
    counter = Counter(filtered)
    return pd.DataFrame(counter.most_common(top_n), columns=['Keyword', 'Count'])


def get_top_bigrams(texts, top_n=15):
    """
    Extract top 2-word phrases (Bigrams) from text list
    Args:
        texts: List of text strings
        top_n: Number of top bigrams to return
    Returns:
        DataFrame with phrases and counts
    """
    if not texts:
        return pd.DataFrame()
    
    stopwords = get_stopwords()
    all_text = " ".join([str(t) for t in texts]).lower()
    words = re.findall(r'\w+', all_text)
    
    bigrams = []
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        if (len(w1) > 2 and len(w2) > 2 and 
            w1 not in stopwords and w2 not in stopwords):
            bigrams.append(f"{w1} {w2}")
    
    counter = Counter(bigrams)
    return pd.DataFrame(counter.most_common(top_n), columns=['Phrase', 'Count'])


def is_rtl_text(text):
    """
    Check if text is primarily right-to-left (Arabic, Hebrew, etc.)
    Args:
        text: String to check
    Returns:
        Boolean indicating if text is RTL
    """
    if not isinstance(text, str):
        return False
    return any("\u0600" <= c <= "\u06FF" for c in text)


def highlight_text(text, search_term):
    """
    Highlight search term in text with HTML mark tags
    Args:
        text: Text to highlight in
        search_term: Term to highlight
    Returns:
        Text with <mark> tags around matches
    """
    if not search_term:
        return text
    
    import html
    text = html.escape(text)
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)