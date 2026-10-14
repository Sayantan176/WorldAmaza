import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict
import httpx
from app.config import settings
from app.schemas.article import ArticleNormalized
from app.services.deduplication_service import canonicalize_url, compute_content_hash
from app.services.rss_service import rss_adapter

logger = logging.getLogger("worldamaze.news")


class BaseNewsSourceAdapter(ABC):
    @abstractmethod
    def fetch_articles(self, query: str, max_articles: int = 10) -> List[ArticleNormalized]:
        """Fetch articles matching query."""
        pass


class GNewsAdapter(BaseNewsSourceAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GNEWS_API_KEY
        self.base_url = "https://gnews.io/api/v4/search"

    def fetch_articles(self, query: str, max_articles: int = 10) -> List[ArticleNormalized]:
        if not self.api_key:
            logger.warning("GNews API key is not configured.")
            return []

        articles: List[ArticleNormalized] = []
        # GNews max limit per request on standard plan is 10
        fetch_limit = min(max_articles, 10)

        # Sanitize query: GNews works best with clean alphanumeric queries
        clean_query = query.strip()
        if not clean_query:
            return []

        params = {
            "q": clean_query,
            "lang": "en",
            "max": fetch_limit,
            "apikey": self.api_key
        }

        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(self.base_url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    raw_articles = data.get("articles", [])
                    for raw in raw_articles:
                        url = canonicalize_url(raw.get("url", ""))
                        if not url:
                            continue

                        title = (raw.get("title") or "").strip()
                        if not title:
                            continue

                        snippet = (raw.get("description") or "").strip()
                        content = raw.get("content")
                        source_info = raw.get("source") or {}
                        source_name = source_info.get("name") or "GNews Source"

                        pub_str = raw.get("publishedAt")
                        published_at = None
                        if pub_str:
                            try:
                                # Standard GNews format is ISO 8601: 2024-03-20T10:15:30Z
                                published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                            except Exception:
                                published_at = None

                        content_hash = compute_content_hash(title, snippet)

                        articles.append(ArticleNormalized(
                            canonical_url=url,
                            title=title,
                            source_name=source_name,
                            author=None,
                            published_at=published_at,
                            retrieved_at=datetime.now(timezone.utc),
                            snippet=snippet,
                            content=content,
                            content_hash=content_hash,
                            source_type="gnews",
                            language="en",
                            source_metadata={"source_url": source_info.get("url")}
                        ))
                elif resp.status_code in (403, 429):
                    logger.warning(f"GNews quota exceeded or rate limit hit (HTTP {resp.status_code}).")
                else:
                    logger.warning(f"GNews API returned error: HTTP {resp.status_code}: {resp.text[:100]}")

        except Exception as e:
            logger.error(f"Error querying GNews API: {type(e).__name__} {e}")

        return articles


class NewsIngestionService:
    def __init__(self):
        self.gnews_adapter = GNewsAdapter()
        self.rss_adapter = rss_adapter

    def discover_articles(self, query: str, max_articles: int = 10, use_rss_fallback: bool = True) -> List[ArticleNormalized]:
        """
        Discovers candidate articles for a query using GNews and RSS feeds.
        Merges results and filters exact duplicates.
        """
        articles: List[ArticleNormalized] = []
        seen_urls = set()
        seen_hashes = set()

        # 1. Try GNews first
        gnews_articles = self.gnews_adapter.fetch_articles(query, max_articles=max_articles)
        for art in gnews_articles:
            if art.canonical_url not in seen_urls and art.content_hash not in seen_hashes:
                seen_urls.add(art.canonical_url)
                seen_hashes.add(art.content_hash)
                articles.append(art)

        # 2. If GNews returns few articles or fails, supplement or fallback with RSS
        if len(articles) < max_articles and use_rss_fallback:
            rss_articles = self.rss_adapter.search_articles(query, max_articles=(max_articles - len(articles)))
            for art in rss_articles:
                if art.canonical_url not in seen_urls and art.content_hash not in seen_hashes:
                    seen_urls.add(art.canonical_url)
                    seen_hashes.add(art.content_hash)
                    articles.append(art)

        return articles


news_ingestion_service = NewsIngestionService()
