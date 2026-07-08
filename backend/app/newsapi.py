# backend/app/newsapi.py
"""
NewsAPI integration for real headline text.
Enriches GDELT events with actual news headlines.
"""

import logging
import requests
from backend.app.config import NEWS_API_KEY

logger = logging.getLogger(__name__)

CRISIS_QUERIES = [
    "earthquake disaster",
    "flood emergency",
    "hurricane cyclone typhoon",
    "wildfire",
    "tsunami warning",
    "volcanic eruption",
    "tornado warning",
    "disease outbreak epidemic",
    "military conflict war",
    "protest riot unrest",
    "drought famine",
    "bridge collapse infrastructure",
]

QUERY_TO_CATEGORY = {
    "earthquake disaster":        "Earthquake",
    "flood emergency":            "Flood",
    "hurricane cyclone typhoon":  "Flood",
    "wildfire":                   "Fire",
    "tsunami warning":            "Tsunami",
    "volcanic eruption":          "Volcanic",
    "tornado warning":            "Tornado",
    "disease outbreak epidemic":  "Outbreak",
    "military conflict war":      "Conflict",
    "protest riot unrest":        "Civic Unrest",
    "drought famine":             "Drought",
    "bridge collapse infrastructure": "Infrastructure",
}


def fetch_crisis_headlines() -> list[dict]:
    """
    Fetches real crisis headlines from NewsAPI.
    Returns events in pipeline-compatible format.
    """
    if not NEWS_API_KEY:
        logger.warning("NewsAPI key not set. Skipping news headlines.")
        return []

    all_articles = []

    for query in CRISIS_QUERIES[:6]:  # Limit to 6 queries to stay within free tier
        try:
            url = (
                f"https://newsapi.org/v2/everything"
                f"?q={query}"
                f"&sortBy=publishedAt"
                f"&pageSize=5"
                f"&language=en"
                f"&apiKey={NEWS_API_KEY}"
            )
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue

            data     = response.json()
            articles = data.get("articles", [])
            category = QUERY_TO_CATEGORY.get(query, "General")

            for article in articles:
                title       = article.get("title", "")
                description = article.get("description", "")
                url_link    = article.get("url", "")
                source_name = article.get("source", {}).get("name", "")

                if not title or title == "[Removed]":
                    continue

                text = f"{title}. {description}" if description else title

                all_articles.append({
                    "id":           f"news_{hash(url_link)}",
                    "text":         text,
                    "category":     category,
                    "lat":          None,
                    "lon":          None,
                    "landmark":     source_name,
                    "source":       "newsapi",
                    "source_url":   url_link,
                    "geotagged":    False,
                    "num_mentions": 5,
                    "credibility":  0.85,
                    "avg_tone":     -3.0,
                })

        except Exception as e:
            logger.debug(f"NewsAPI fetch failed for '{query}': {e}")

    logger.info(f"NewsAPI: {len(all_articles)} headlines fetched.")
    return all_articles