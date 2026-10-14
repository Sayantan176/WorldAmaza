import logging
from typing import List, Dict, Any
from app.schemas.article import ArticleNormalized

logger = logging.getLogger("worldamaze.summary")


def format_grounded_summary(
    headline: str,
    raw_summary: str,
    what_changed: str,
    evidence_status: str,
    articles: List[ArticleNormalized],
) -> Dict[str, Any]:
    """
    Constructs a verified, source-grounded intelligence summary package
    with explicit attribution links.
    """
    sources_list = []
    for art in articles:
        sources_list.append({
            "source_name": art.source_name,
            "title": art.title,
            "url": art.canonical_url,
            "published_at": art.published_at.isoformat() if art.published_at else None,
        })

    # Evidence status note
    status_notes = {
        "official_confirmed": "Officially confirmed by government or corporate sources.",
        "multiple_sources": "Corroborated across multiple independent reporting outlets.",
        "single_report": "Reported by a single source; awaiting independent verification.",
        "unverified_rumor": "Unverified report or market rumor; not officially corroborated.",
        "speculative": "Analytical commentary or speculative scenario; no confirmed event.",
    }
    evidence_note = status_notes.get(evidence_status, "Verification status pending.")

    return {
        "headline": headline.strip(),
        "summary": raw_summary.strip(),
        "what_changed": what_changed.strip(),
        "evidence_status": evidence_status,
        "evidence_note": evidence_note,
        "sources": sources_list,
    }
