# backend/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- City & Landmarks (kept for reference) ---
CITY_NAME   = "Global"
CITY_ANCHOR = {"lat": 20.0, "lon": 10.0}
LANDMARKS   = {}

# --- Categories ---
CATEGORIES = [
    "Fire", "Flood", "Earthquake", "Tsunami", "Tornado",
    "Volcanic", "Landslide", "Drought", "Civic Unrest",
    "Outbreak", "Conflict", "Infrastructure", "General"
]
CRISIS_CATEGORIES = [
    "Fire", "Flood", "Earthquake", "Tsunami", "Tornado",
    "Volcanic", "Landslide", "Drought", "Civic Unrest",
    "Outbreak", "Conflict", "Infrastructure"
]

# --- ST-DBSCAN Parameters ---
DBSCAN_EPS           = 0.01
DBSCAN_MIN_SAMPLES   = 4
TEMPORAL_EPS_MINUTES = 3.0

# --- Anomaly Detection ---
ANOMALY_Z_SCORE_THRESHOLD = 3.0
MIN_ALERT_SIZE            = 4
HISTORICAL_WINDOW_MINUTES = 30
ANOMALY_WARMUP_BINS       = 5

# --- Alert Lifecycle ---
ACTIVE_ALERT_TIMEOUT_SECONDS = 300
MAX_RESOLVED_ALERTS          = 50

# --- Analytics ---
ANALYTICS_INTERVAL_SECONDS = 3.0
ROLLING_WINDOW_MINUTES      = 10

# --- API & Feed ---
MAX_TWEETS_IN_MEMORY = 1000
API_TWEET_FETCH_LIMIT = 100
MAX_LANDMARK_DISTANCE = 0.05

# --- Severity Weights ---
SEVERITY_WEIGHTS = {
    "Earthquake":  1.5,
    "Tsunami":     2.0,
    "Volcanic":    1.8,
    "Tornado":     1.6,
    "Conflict":    1.4,
    "Outbreak":    1.3,
    "Flood":       1.2,
    "Landslide":   1.2,
    "Fire":        1.1,
    "Civic Unrest":1.0,
    "Drought":     0.9,
    "Infrastructure": 0.8,
    "General":     0.5,
}

# --- API Keys ---
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY", "")
SLACK_WEBHOOK_URL    = os.getenv("SLACK_WEBHOOK_URL", "")
OPENWEATHER_API_KEY  = os.getenv("OPENWEATHER_API_KEY", "")
NEWS_API_KEY         = os.getenv("NEWS_API_KEY", "")
TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")