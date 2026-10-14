import logging
from datetime import datetime, timezone
from typing import List, Optional
import feedparser
import httpx
from app.schemas.article import ArticleNormalized
from app.services.deduplication_service import canonicalize_url, compute_content_hash

logger = logging.getLogger("worldamaze.rss")

# Reputable, general and domain-specific open RSS feeds
DEFAULT_RSS_FEEDS = [
    {"name": "BBC News - World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC News - Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
    {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"},
    {"name": "Defense One", "url": "https://www.defenseone.com/rss/all/"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "Al Jazeera - English", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]


class RSSAdapter:
    def __init__(self, feeds: Optional[List[dict]] = None):
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    def fetch_feed_articles(self, feed_url: str, source_name: str) -> List[ArticleNormalized]:
        articles = []
        try:
            # Fetch with httpx with reasonable timeout and standard user agent
            headers = {"User-Agent": "WorldAmaze-Monitor/1.0 (+https://worldamaze.ai)"}
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                resp = client.get(feed_url)
                if resp.status_code != 200:
                    logger.warning(f"RSS feed {source_name} returned status {resp.status_code}")
                    return []
                feed_data = feedparser.parse(resp.text)

            for entry in feed_data.entries[:25]:
                raw_url = getattr(entry, "link", "")
                canon_url = canonicalize_url(raw_url)
                if not canon_url:
                    continue

                title = getattr(entry, "title", "").strip()
                if not title:
                    continue

                snippet = getattr(entry, "summary", "") or getattr(entry, "description", "")
                # Strip HTML tags if any
                clean_snippet = re_clean_html(snippet)[:800]

                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pub_date = None

                author = getattr(entry, "author", None)
                content_hash = compute_content_hash(title, clean_snippet)

                articles.append(ArticleNormalized(
                    canonical_url=canon_url,
                    title=title,
                    source_name=source_name,
                    author=author,
                    published_at=pub_date,
                    retrieved_at=datetime.now(timezone.utc),
                    snippet=clean_snippet,
                    content=None,
                    content_hash=content_hash,
                    source_type="rss",
                    language="en",
                    source_metadata={"feed_url": feed_url}
                ))
        except Exception as e:
            logger.warning(f"Error fetching RSS feed {source_name} ({feed_url}): {e}")
        return articles

    def search_articles(self, query: str, max_articles: int = 10) -> List[ArticleNormalized]:
        """
        Searches recent articles from registered RSS feeds matching query keywords.
        """
        all_articles: List[ArticleNormalized] = []
        keywords = [k.lower() for k in query.split() if len(k) > 2]

        for feed in self.feeds:
            feed_articles = self.fetch_feed_articles(feed["url"], feed["name"])
            for art in feed_articles:
                content_to_check = f"{art.title} {art.snippet}".lower()
                # Check keyword match
                if any(kw in content_to_check for kw in keywords):
                    all_articles.append(art)
                if len(all_articles) >= max_articles:
                    break
            if len(all_articles) >= max_articles:
                break

        return all_articles[:max_articles]


def re_clean_html(raw_html: str) -> str:
    import re
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    return " ".join(clean.split())


rss_adapter = RSSAdapter()
