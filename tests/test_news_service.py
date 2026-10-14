from unittest.mock import patch, MagicMock
from app.services.news_service import GNewsAdapter, NewsIngestionService
from app.services.rss_service import RSSAdapter


def test_gnews_adapter_success():
    adapter = GNewsAdapter(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "totalArticles": 1,
        "articles": [
            {
                "title": "India signs major contract for 97 Tejas fighter jets",
                "description": "The Defence Ministry has finalized the procurement deal.",
                "content": "Full article text describing the procurement.",
                "url": "https://www.reuters.com/defence/india-tejas-contract/?utm_source=rss",
                "image": "https://reuters.com/img.jpg",
                "publishedAt": "2026-03-15T09:30:00Z",
                "source": {
                    "name": "Reuters",
                    "url": "https://www.reuters.com"
                }
            }
        ]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        articles = adapter.fetch_articles("Tejas fighter", max_articles=5)

    assert len(articles) == 1
    art = articles[0]
    assert art.title == "India signs major contract for 97 Tejas fighter jets"
    assert art.source_name == "Reuters"
    assert art.canonical_url == "https://reuters.com/defence/india-tejas-contract"
    assert art.content_hash is not None
    assert art.published_at is not None


def test_gnews_adapter_quota_exhaustion():
    adapter = GNewsAdapter(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Quota exceeded"

    with patch("httpx.Client.get", return_value=mock_resp):
        articles = adapter.fetch_articles("Tejas", max_articles=5)

    # Should gracefully return empty list without throwing
    assert articles == []


def test_news_ingestion_rss_fallback():
    service = NewsIngestionService()

    # When GNews returns empty list, RSS should be searched as fallback
    with patch.object(service.gnews_adapter, "fetch_articles", return_value=[]):
        with patch.object(service.rss_adapter, "search_articles") as mock_rss:
            mock_rss.return_value = []
            service.discover_articles("cybersecurity zero-day", max_articles=5, use_rss_fallback=True)
            mock_rss.assert_called_once()
