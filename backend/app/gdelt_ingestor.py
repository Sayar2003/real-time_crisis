# backend/app/gdelt_ingestor.py

import io
import time
import uuid
import logging
import asyncio
import requests
import pandas as pd
from datetime import datetime, timezone
from backend.app.config import CRISIS_CATEGORIES

logger = logging.getLogger(__name__)

# GDELT event codes that map to our crisis categories
# Full codebook: http://data.gdeltproject.org/documentation/CAMEO.Manual.CAMEO.pdf
GDELT_EVENT_CODE_MAP = {
    "Fire": [
        "0251",  # Appeal for humanitarian aid
        "2041",  # Use conventional military force
        "180",   # Use unconventional mass violence
        "1831",  # Threaten unconventional attack
    ],
    "Flood": [
        "0251",  # Natural disaster appeal
        "0242",  # Appeal for economic aid
    ],
    "Civic Unrest": [
        "145",   # Protest violently
        "1451",  # Engage in strike or boycott
        "1452",  # Conduct hunger strike
        "1453",  # Conduct sit-in
        "1454",  # Conduct march or rally
        "146",   # Revolt
        "1461",  # Mutiny
        "1462",  # Engage in armed battle
        "173",   # Impose curfew
        "174",   # Impose state of emergency
        "175",   # Impose martial law
    ],
    "Outbreak": [
        "0251",  # Appeal for humanitarian aid
        "0243",  # Appeal for medical aid
        "0244",  # Appeal for military aid
    ],
}

# GDELT QuadClass codes for filtering
# 1=Verbal Cooperation, 2=Material Cooperation, 3=Verbal Conflict, 4=Material Conflict
CRISIS_QUAD_CLASSES = [3, 4]  # Focus on conflict events

# Keywords in source URLs/names that indicate crisis news
CRISIS_KEYWORDS = {
    "Fire":         ["fire", "explosion", "blast", "blaze", "burn"],
    "Flood":        ["flood", "storm", "hurricane", "cyclone", "typhoon", "tsunami"],
    "Civic Unrest": ["protest", "riot", "unrest", "demonstration", "clash", "coup"],
    "Outbreak":     ["outbreak", "epidemic", "virus", "disease", "infection", "quarantine"],
}


class GDELTIngestor:
    """
    Polls GDELT 2.0 Event Database every 15 minutes for real crisis events.
    Converts GDELT rows into tweet-format dicts compatible with our pipeline.
    """

    GDELT_LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    POLL_INTERVAL = 900  # 15 minutes in seconds

    def __init__(self):
        self.last_fetched_url = None
        self.events_ingested = 0

    def _get_latest_csv_url(self) -> str | None:
        """Fetches the URL of the latest GDELT event CSV file."""
        try:
            response = requests.get(self.GDELT_LASTUPDATE_URL, timeout=10)
            response.raise_for_status()
            # File lists 3 URLs — we want the first one (events file)
            lines = response.text.strip().split("\n")
            for line in lines:
                parts = line.strip().split(" ")
                if len(parts) == 3 and "export" in parts[2]:
                    return parts[2].strip()
        except Exception as e:
            logger.error(f"Failed to fetch GDELT lastupdate: {e}")
        return None

    def _fetch_events(self, csv_url: str) -> pd.DataFrame:
        """Downloads and parses the GDELT CSV file."""
        try:
            logger.info(f"Fetching GDELT data from: {csv_url}")
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()

            # GDELT CSV has no header — we define column names
            # Full schema: http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
            cols = [
                "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
                "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
                "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
                "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
                "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
                "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
                "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
                "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode",
                "QuadClass", "GoldsteinScale", "NumMentions", "NumSources",
                "NumArticles", "AvgTone", "Actor1Geo_Type", "Actor1Geo_FullName",
                "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code", "Actor1Geo_ADM2Code",
                "Actor1Geo_Lat", "Actor1Geo_Long", "Actor1Geo_FeatureID",
                "Actor2Geo_Type", "Actor2Geo_FullName", "Actor2Geo_CountryCode",
                "Actor2Geo_ADM1Code", "Actor2Geo_ADM2Code", "Actor2Geo_Lat",
                "Actor2Geo_Long", "Actor2Geo_FeatureID", "ActionGeo_Type",
                "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
                "ActionGeo_ADM2Code", "ActionGeo_Lat", "ActionGeo_Long",
                "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL"
            ]

            import zipfile
            from io import BytesIO
            zip_bytes = BytesIO(response.content)
            with zipfile.ZipFile(zip_bytes) as z:
                csv_filename = z.namelist()[0]
                with z.open(csv_filename) as f:
                    df = pd.read_csv(f, sep="\t", header=None, names=cols,
                                     dtype=str, on_bad_lines="skip")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch/parse GDELT CSV: {e}")
            return pd.DataFrame()

    def _classify_event(self, row: pd.Series) -> str | None:
        """
        Maps a GDELT event row to one of our crisis categories.
        Returns None if the event is not crisis-relevant.
        """
        source_url = str(row.get("SOURCEURL", "")).lower()
        event_code = str(row.get("EventCode", ""))

        try:
            quad_class = int(row.get("QuadClass", 0))
        except (ValueError, TypeError):
            quad_class = 0

        # Only process conflict events
        if quad_class not in CRISIS_QUAD_CLASSES:
            return None

        # Check keywords in source URL for category
        for category, keywords in CRISIS_KEYWORDS.items():
            for kw in keywords:
                if kw in source_url:
                    return category

        # Check event codes
        for category, codes in GDELT_EVENT_CODE_MAP.items():
            if event_code in codes:
                return category

        return None

    def _row_to_tweet(self, row: pd.Series, category: str) -> dict | None:
        """Converts a GDELT event row to our internal tweet format."""
        try:
            lat = float(row.get("ActionGeo_Lat", "") or 0)
            lon = float(row.get("ActionGeo_Long", "") or 0)

            if lat == 0.0 and lon == 0.0:
                return None  # Skip events with no location

            location = str(row.get("ActionGeo_FullName", "Unknown Location"))
            source_url = str(row.get("SOURCEURL", ""))
            num_mentions = int(row.get("NumMentions", 1) or 1)
            avg_tone = float(row.get("AvgTone", 0) or 0)

            # Generate descriptive text from available fields
            text = self._generate_text(category, location, source_url, avg_tone)

            return {
                "id":            f"gdelt_{row.get('GLOBALEVENTID', uuid.uuid4())}",
                "text":          text,
                "timestamp":     time.time(),
                "true_category": category,
                "geotagged":     True,
                "lat":           lat,
                "lon":           lon,
                "source":        "gdelt",
                "source_url":    source_url,
                "num_mentions":  num_mentions,
                "credibility":   min(num_mentions / 10.0, 1.0),  # simple credibility score
            }
        except Exception as e:
            logger.debug(f"Failed to convert GDELT row: {e}")
            return None

    def _generate_text(self, category: str, location: str, url: str, tone: float) -> str:
        """Generates a human-readable description from GDELT event data."""
        severity = "severe" if tone < -5 else "moderate"
        templates = {
            "Fire":         f"Reports of {severity} fire or explosion incident in {location}.",
            "Flood":        f"Flooding or severe storm event reported in {location}.",
            "Civic Unrest": f"Civil unrest and protests reported in {location}.",
            "Outbreak":     f"Disease outbreak or health emergency reported in {location}.",
        }
        return templates.get(category, f"Crisis event detected in {location}.")

    def fetch_latest(self) -> list[dict]:
        """
        Fetches the latest GDELT update and returns crisis events
        as tweet-format dicts ready for the pipeline.
        """
        csv_url = self._get_latest_csv_url()
        if not csv_url:
            return []

        # Skip if we already processed this file
        if csv_url == self.last_fetched_url:
            logger.info("GDELT: No new update available yet.")
            return []

        self.last_fetched_url = csv_url
        df = self._fetch_events(csv_url)

        if df.empty:
            return []

        crisis_tweets = []
        for _, row in df.iterrows():
            category = self._classify_event(row)
            if category is None:
                continue
            tweet = self._row_to_tweet(row, category)
            if tweet:
                crisis_tweets.append(tweet)

        self.events_ingested += len(crisis_tweets)
        logger.info(f"GDELT: Ingested {len(crisis_tweets)} crisis events from latest update.")
        return crisis_tweets


# Global instance
gdelt_ingestor = GDELTIngestor()


def get_gdelt_ingestor() -> GDELTIngestor:
    return gdelt_ingestor