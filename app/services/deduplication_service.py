import hashlib
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Set, Tuple


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "ref_src", "source", "ocid",
    "ncid", "guccounter", "ved", "usg"
}


def canonicalize_url(url: str) -> str:
    """
    Normalizes a URL by stripping tracking query params, fragments,
    and standardizing host/scheme/path.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        # Filter query params
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        cleaned_pairs = [(k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS]
        cleaned_pairs.sort(key=lambda x: x[0])
        clean_query = urlencode(cleaned_pairs)
        
        # Normalize path
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        
        return urlunparse((scheme, netloc, path, "", clean_query, ""))
    except Exception:
        return url.strip()


def normalize_text_for_hash(text: str) -> str:
    """Normalizes text by removing punctuation, extra whitespace, and lowercasing."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    tokens = text.split()
    return " ".join(tokens)


def compute_content_hash(title: str, snippet: str = "") -> str:
    """Computes a stable SHA-256 hash for deterministic deduplication."""
    norm_title = normalize_text_for_hash(title)
    norm_snippet = normalize_text_for_hash(snippet[:200])
    combined = f"{norm_title}|{norm_snippet}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def tokenize(text: str) -> Set[str]:
    """Tokenizes text into a set of normalized non-trivial words."""
    norm = normalize_text_for_hash(text)
    stopwords = {"and", "the", "for", "with", "from", "about", "into", "that", "this", "after", "over"}
    return {w for w in norm.split() if len(w) > 2 and w not in stopwords}


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates token Jaccard similarity between two texts."""
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def generate_event_dedup_key(headline: str, category: str, topic_key: str) -> str:
    """
    Generates a deterministic clustering key for an event based on
    topic key, normalized headline tokens, and category.
    """
    norm_topic = normalize_text_for_hash(topic_key).replace(" ", "-")[:40]
    tokens = sorted(list(tokenize(headline)))[:5]
    token_str = "-".join(tokens)
    raw = f"{category}:{norm_topic}:{token_str}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]
