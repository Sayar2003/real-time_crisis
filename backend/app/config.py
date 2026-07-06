# backend/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- City & Landmarks ---
# --- Multi-City Configuration ---
MONITORED_REGIONS = {
    "london": {
        "anchor": {"lat": 51.5074, "lon": -0.1278},
        "landmarks": {
            "big ben":            (51.5007, -0.1246),
            "hyde park":          (51.5073, -0.1657),
            "london eye":         (51.5033, -0.1195),
            "tower bridge":       (51.5055, -0.0754),
            "buckingham palace":  (51.5014, -0.1419),
            "trafalgar square":   (51.5080, -0.1281),
            "british museum":     (51.5194, -0.1270),
            "soho":               (51.5136, -0.1365),
            "covent garden":      (51.5117, -0.1240),
            "piccadilly circus":  (51.5101, -0.1342),
        }
    },
    "new_delhi": {
        "anchor": {"lat": 28.6139, "lon": 77.2090},
        "landmarks": {
            "india gate":         (28.6129, 77.2295),
            "connaught place":    (28.6315, 77.2167),
            "red fort":           (28.6562, 77.2410),
            "chandni chowk":      (28.6506, 77.2334),
            "saket":              (28.5244, 77.2066),
            "lajpat nagar":       (28.5677, 77.2433),
            "nehru place":        (28.5491, 77.2519),
            "dwarka":             (28.5921, 77.0460),
        }
    },
    "dhaka": {
        "anchor": {"lat": 23.8103, "lon": 90.4125},
        "landmarks": {
            "motijheel":          (23.7338, 90.4177),
            "gulshan":            (23.7808, 90.4152),
            "dhanmondi":          (23.7461, 90.3742),
            "old dhaka":          (23.7104, 90.4074),
            "mirpur":             (23.8223, 90.3654),
            "uttara":             (23.8759, 90.3795),
            "shahbag":            (23.7388, 90.3950),
        }
    },
    "jakarta": {
        "anchor": {"lat": -6.2088, "lon": 106.8456},
        "landmarks": {
            "monas":              (-6.1754, 106.8272),
            "kota tua":           (-6.1352, 106.8133),
            "glodok":             (-6.1489, 106.8167),
            "sudirman":           (-6.2088, 106.8175),
            "kemang":             (-6.2607, 106.8133),
            "tanah abang":        (-6.1864, 106.8133),
            "senen":              (-6.1764, 106.8455),
        }
    }
}

# Flatten for backward compatibility — code that imports LANDMARKS still works
LANDMARKS = {
    landmark: coords
    for region in MONITORED_REGIONS.values()
    for landmark, coords in region["landmarks"].items()
}

# Keep CITY_ANCHOR pointing to London for backward compatibility
CITY_NAME = "London"
CITY_ANCHOR = MONITORED_REGIONS["london"]["anchor"]

# List of all region anchors for map centering
REGION_ANCHORS = [
    {"name": name, **data["anchor"]}
    for name, data in MONITORED_REGIONS.items()
]

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