# backend/app/config.py

CITY_NAME = "London"
CITY_ANCHOR = {"lat": 51.5074, "lon": -0.1278}

# Mapping of landmarks to their geographical coordinates (lat, lon)
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

# Categories definition
CATEGORIES = ["General", "Fire", "Flood", "Civic Unrest", "Outbreak"]
CRISIS_CATEGORIES = ["Fire", "Flood", "Civic Unrest", "Outbreak"]

# ST-DBSCAN Parameters
DBSCAN_EPS = 0.01  # Maximum spatial distance in degrees (~1.1 km)
DBSCAN_MIN_SAMPLES = 4  # Minimum points to form a cluster
TEMPORAL_EPS_MINUTES = 3.0  # Maximum temporal distance in minutes

# Anomaly Detection Parameters
ANOMALY_Z_SCORE_THRESHOLD = 3.0
MIN_ALERT_SIZE = 4  # Min tweets in a cluster to trigger an alert
HISTORICAL_WINDOW_MINUTES = 30  # Baseline window for calculating mean/std

# Stream Ingestion Parameters
SIMULATION_TWEET_RATE = 2.0  # Background tweets per second
ACTIVE_ALERT_TIMEOUT_SECONDS = 15  # Seconds without new tweets before resolving alert
ROLLING_WINDOW_MINUTES = 10  # Sliding memory window size in minutes
