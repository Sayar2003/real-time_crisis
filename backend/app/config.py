# backend/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- City & Landmarks ---
CITY_NAME = "London"
CITY_ANCHOR = {"lat": 51.5074, "lon": -0.1278}

LANDMARKS = {
    "big ben": (51.5007, -0.1246),
    "hyde park": (51.5073, -0.1657),
    "london eye": (51.5033, -0.1195),
    "tower bridge": (51.5055, -0.0754),
    "buckingham palace": (51.5014, -0.1419),
    "trafalgar square": (51.5080, -0.1281),
    "british museum": (51.5194, -0.1270),
    "soho": (51.5136, -0.1365),
    "covent garden": (51.5117, -0.1240),
    "piccadilly circus": (51.5101, -0.1342)
}

# --- Categories ---
CATEGORIES = ["General", "Fire", "Flood", "Civic Unrest", "Outbreak"]
CRISIS_CATEGORIES = ["Fire", "Flood", "Civic Unrest", "Outbreak"]

# --- ST-DBSCAN Parameters ---
DBSCAN_EPS = 0.01            # Maximum spatial distance in degrees (~1.1 km)
DBSCAN_MIN_SAMPLES = 4       # Minimum points to form a cluster
TEMPORAL_EPS_MINUTES = 3.0   # Maximum temporal distance in minutes

# --- Anomaly Detection Parameters ---
ANOMALY_Z_SCORE_THRESHOLD = 3.0
MIN_ALERT_SIZE = 4
HISTORICAL_WINDOW_MINUTES = 30
ANOMALY_WARMUP_BINS = 5      # Min non-zero bins before Z-score alerts can fire

# --- Alert Lifecycle ---
ACTIVE_ALERT_TIMEOUT_SECONDS = 300   # 5 minutes (was 15 — too short for demos)
MAX_RESOLVED_ALERTS = 50

# --- Stream Ingestion ---
SIMULATION_TWEET_RATE = 2.0          # Background tweets per second
SIMULATION_BURST_RATE = 15.0         # Crisis injection tweets per second
SIMULATION_BURST_JITTER = 0.3        # Random spread radius during burst (degrees)
ROLLING_WINDOW_MINUTES = 10          # Sliding memory window for clustering

# --- Analytics Worker ---
ANALYTICS_INTERVAL_SECONDS = 3.0     # How often analytics worker runs (was hardcoded)

# --- API & Feed ---
MAX_TWEETS_IN_MEMORY = 1000          # Cap on rolling tweet store
API_TWEET_FETCH_LIMIT = 30           # Default tweet fetch limit
MAX_LANDMARK_DISTANCE = 0.05         # Max degrees to assign a landmark (~5.5 km)

# --- API Keys (loaded from .env) ---
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL    = os.getenv("SLACK_WEBHOOK_URL", "")