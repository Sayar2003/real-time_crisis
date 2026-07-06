# backend/app/gdelt_ingestor.py

import io
import time
import uuid
import logging
import zipfile
import requests
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

# Expanded crisis keyword map covering more event types
CRISIS_KEYWORDS = {
    "Fire": [
        "fire", "wildfire", "bushfire", "explosion", "blast",
        "blaze", "burning", "inferno", "arson", "firestorm"
    ],
    "Flood": [
        "flood", "flooding", "flash flood", "storm surge", "inundation",
        "deluge", "waterlogged", "submerged", "overflow", "cyclone",
        "hurricane", "typhoon", "monsoon"
    ],
    "Earthquake": [
        "earthquake", "quake", "tremor", "seismic", "aftershock",
        "magnitude", "richter", "epicenter", "fault line"
    ],
    "Tsunami": [
        "tsunami", "tidal wave", "ocean wave", "seismic wave", "wave warning"
    ],
    "Tornado": [
        "tornado", "twister", "funnel cloud", "windstorm", "supercell",
        "cyclone warning", "wind damage"
    ],
    "Volcanic": [
        "volcano", "volcanic", "eruption", "lava", "ash cloud",
        "magma", "pyroclastic", "volcanic ash"
    ],
    "Landslide": [
        "landslide", "mudslide", "rockslide", "avalanche", "debris flow",
        "mudflow", "slope failure"
    ],
    "Drought": [
        "drought", "water shortage", "water crisis", "famine",
        "crop failure", "food shortage", "dry spell"
    ],
    "Civic Unrest": [
        "protest", "riot", "unrest", "demonstration", "clash",
        "coup", "uprising", "revolution", "violence", "crackdown",
        "martial law", "curfew", "conflict"
    ],
    "Outbreak": [
        "outbreak", "epidemic", "pandemic", "virus", "disease",
        "infection", "quarantine", "health emergency", "contamination",
        "pathogen", "cholera", "dengue", "ebola", "malaria"
    ],
    "Conflict": [
        "war", "attack", "bombing", "airstrike", "missile",
        "military", "troops", "casualties", "ceasefire", "invasion",
        "shelling", "gunfire", "armed"
    ],
    "Infrastructure": [
        "blackout", "power outage", "grid failure", "bridge collapse",
        "building collapse", "pipeline", "dam failure", "infrastructure"
    ],
}

# GDELT QuadClass — focus on conflict and crisis events
CRISIS_QUAD_CLASSES = [3, 4]

# GDELT event codes mapping to categories
GDELT_EVENT_CODES = {
    "Civic Unrest": ["14", "145", "146", "173", "174", "175"],
    "Conflict":     ["19", "190", "193", "194", "195", "196"],
    "Outbreak":     ["0243", "0244"],
}


class GDELTIngestor:
    GDELT_LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    POLL_INTERVAL = 900  # 15 minutes

    def __init__(self):
        self.last_fetched_url = None
        self.events_ingested  = 0

    def _get_latest_csv_url(self) -> str | None:
        try:
            response = requests.get(self.GDELT_LASTUPDATE_URL, timeout=10)
            response.raise_for_status()
            for line in response.text.strip().split("\n"):
                parts = line.strip().split(" ")
                if len(parts) == 3 and "export" in parts[2]:
                    return parts[2].strip()
        except Exception as e:
            logger.error(f"Failed to fetch GDELT lastupdate: {e}")
        return None

    def _fetch_events(self, csv_url: str) -> pd.DataFrame:
        try:
            logger.info(f"Fetching GDELT data from: {csv_url}")
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()

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

            zip_bytes = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_bytes) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(
                        f, sep="\t", header=None, names=cols,
                        dtype=str, on_bad_lines="skip"
                    )
            return df

        except Exception as e:
            logger.error(f"Failed to fetch/parse GDELT CSV: {e}")
            return pd.DataFrame()

    def _classify_event(self, row: pd.Series) -> str | None:
        source_url  = str(row.get("SOURCEURL", "")).lower()
        event_code  = str(row.get("EventCode", ""))
        actor1      = str(row.get("Actor1Name", "")).lower()
        actor2      = str(row.get("Actor2Name", "")).lower()
        location    = str(row.get("ActionGeo_FullName", "")).lower()
        combined    = f"{source_url} {actor1} {actor2} {location}"

        try:
            quad_class = int(row.get("QuadClass", 0))
        except (ValueError, TypeError):
            quad_class = 0

        # Check keywords in combined text
        for category, keywords in CRISIS_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    return category

        # Check GDELT event codes
        for category, codes in GDELT_EVENT_CODES.items():
            for code in codes:
                if event_code.startswith(code):
                    return category

        # Only include conflict quad class events even without keyword match
        if quad_class in CRISIS_QUAD_CLASSES:
            return "Conflict"

        return None

    def _generate_text(self, category: str, location: str,
                       url: str, tone: float, mentions: int) -> str:
        severity = "severe" if tone < -5 else "significant" if tone < -2 else "emerging"
        source   = url.split("/")[2] if "/" in url else "news source"
        source   = source.replace("www.", "")

        templates = {
            "Fire":           f"{severity.title()} fire or explosion reported in {location}. Multiple sources confirming the incident.",
            "Flood":          f"{severity.title()} flooding or storm event reported in {location}. Emergency services responding.",
            "Earthquake":     f"Earthquake detected near {location}. Reports of ground shaking and potential structural damage.",
            "Tsunami":        f"Tsunami warning issued for {location}. Coastal evacuation orders being considered.",
            "Tornado":        f"Tornado or severe windstorm reported in {location}. Residents urged to seek shelter immediately.",
            "Volcanic":       f"Volcanic activity reported near {location}. Ash cloud and lava flow monitoring underway.",
            "Landslide":      f"Landslide or mudslide reported in {location}. Roads blocked, rescue operations initiated.",
            "Drought":        f"Severe drought conditions reported in {location}. Water shortage affecting local population.",
            "Civic Unrest":   f"Civil unrest and protests reported in {location}. Security forces deployed to maintain order.",
            "Outbreak":       f"Disease outbreak reported in {location}. Health authorities investigating {mentions} confirmed cases.",
            "Conflict":       f"Armed conflict or military action reported in {location}. {mentions} news sources reporting casualties.",
            "Infrastructure": f"Critical infrastructure failure reported in {location}. Emergency crews responding to the incident.",
        }
        return templates.get(category, f"Crisis event detected in {location}. Monitoring situation closely.")

    def _row_to_event(self, row: pd.Series, category: str) -> dict | None:
        try:
            lat = float(row.get("ActionGeo_Lat") or 0)
            lon = float(row.get("ActionGeo_Long") or 0)

            if lat == 0.0 and lon == 0.0:
                return None

            # Filter out invalid coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return None

            location    = str(row.get("ActionGeo_FullName", "Unknown Location"))
            source_url  = str(row.get("SOURCEURL", ""))
            num_mentions = int(row.get("NumMentions", 1) or 1)
            avg_tone    = float(row.get("AvgTone", 0) or 0)
            num_articles = int(row.get("NumArticles", 1) or 1)

            # Credibility score based on number of sources
            credibility = min(num_mentions / 20.0, 1.0)

            text = self._generate_text(category, location, source_url, avg_tone, num_mentions)

            return {
                "id":            f"gdelt_{row.get('GLOBALEVENTID', uuid.uuid4())}",
                "text":          text,
                "timestamp":     time.time(),
                "true_category": category,
                "category":      category,
                "geotagged":     True,
                "lat":           lat,
                "lon":           lon,
                "landmark":      location,
                "source":        "gdelt",
                "source_url":    source_url,
                "num_mentions":  num_mentions,
                "num_articles":  num_articles,
                "avg_tone":      round(avg_tone, 2),
                "credibility":   round(credibility, 2),
            }
        except Exception as e:
            logger.debug(f"Failed to convert GDELT row: {e}")
            return None

    def fetch_latest(self) -> list[dict]:
        csv_url = self._get_latest_csv_url()
        if not csv_url:
            return []

        if csv_url == self.last_fetched_url:
            logger.info("GDELT: No new update available yet.")
            return []

        self.last_fetched_url = csv_url
        df = self._fetch_events(csv_url)

        if df.empty:
            return []

        crisis_events = []
        for _, row in df.iterrows():
            category = self._classify_event(row)
            if category is None:
                continue
            event = self._row_to_event(row, category)
            if event:
                crisis_events.append(event)

        self.events_ingested += len(crisis_events)
        logger.info(f"GDELT: Ingested {len(crisis_events)} crisis events from latest update.")
        return crisis_events


gdelt_ingestor = GDELTIngestor()

def get_gdelt_ingestor() -> GDELTIngestor:
    return gdelt_ingestor