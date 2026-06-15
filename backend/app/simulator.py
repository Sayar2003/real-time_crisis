# backend/app/simulator.py

import random
import time
import uuid
from typing import Dict, List, Optional
from backend.app.config import CITY_NAME, CITY_ANCHOR, LANDMARKS, CRISIS_CATEGORIES, MONITORED_REGIONS

from backend.app.templates import BACKGROUND_TEMPLATES, CRISIS_TEMPLATES

# Stores active simulated crises
# Structure: {crisis_id: {category, landmark, lat, lon, start_time, duration_seconds}}
active_crises: Dict[str, dict] = {}

def get_random_landmark() -> str:
    """Picks a random landmark from any monitored city."""
    return random.choice(list(LANDMARKS.keys()))

def get_random_region_anchor() -> dict:
    """Picks a random city anchor for noise tweet generation."""
    region = random.choice(list(MONITORED_REGIONS.values()))
    return region["anchor"]

def generate_noise_tweet() -> dict:
    landmark = get_random_landmark()
    template = random.choice(BACKGROUND_TEMPLATES)
    text = template.format(landmark=landmark.title())

    if random.random() < 0.7:
        lat_base, lon_base = LANDMARKS[landmark]
        lat = lat_base + random.uniform(-0.001, 0.001)
        lon = lon_base + random.uniform(-0.001, 0.001)
    else:
        lat, lon = None, None

    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "timestamp": time.time(),
        "true_category": "General",
        "geotagged": lat is not None,
        "lat": lat,
        "lon": lon
    }

def generate_crisis_tweet(crisis: dict) -> dict:
    category = crisis["category"]
    landmark = crisis["landmark"]
    lat_base = crisis["lat"]
    lon_base = crisis["lon"]
    
    template = random.choice(CRISIS_TEMPLATES[category])
    text = template.format(landmark=landmark.title())
    
    # Crisis tweets are highly likely to be geotagged, simulating users posting from the scene
    if random.random() < 0.9:
        # Clustered tightly around the epicenter
        lat = lat_base + random.gauss(0, 0.001)
        lon = lon_base + random.gauss(0, 0.001)
    else:
        lat, lon = None, None
        
    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "timestamp": time.time(),
        "true_category": category,
        "geotagged": lat is not None,
        "lat": lat,
        "lon": lon
    }

def inject_crisis_event(category: str, landmark_name: str, duration: int = 40) -> str:
    """Manually injects an active crisis event in the simulator."""
    landmark_key = landmark_name.lower().strip()
    if landmark_key in LANDMARKS:
        lat, lon = LANDMARKS[landmark_key]
    else:
        # Fallback to random city anchor + minor offset
        anchor = get_random_region_anchor()
        lat = anchor["lat"] + random.uniform(-0.02, 0.02)
        lon = anchor["lon"] + random.uniform(-0.02, 0.02)
        landmark_name = "Custom Location"
        
    crisis_id = str(uuid.uuid4())
    active_crises[crisis_id] = {
        "id": crisis_id,
        "category": category,
        "landmark": landmark_name,
        "lat": lat,
        "lon": lon,
        "start_time": time.time(),
        "duration": duration
    }
    return crisis_id

def prune_expired_crises():
    """Removes crises that have completed their duration."""
    now = time.time()
    expired = [
        cid for cid, crisis in active_crises.items()
        if now - crisis["start_time"] > crisis["duration"]
    ]
    for cid in expired:
        active_crises.pop(cid)

def generate_next_tweet() -> dict:
    """Generates the next tweet in the stream, incorporating background and crisis signals."""
    prune_expired_crises()
    
    # 10% chance to randomly spawn a crisis if there are none active
    # 2% chance to spawn additional crisis regardless of existing ones
    if random.random() < 0.02:
        cat = random.choice(CRISIS_CATEGORIES)
        inject_crisis_event(cat, get_random_landmark(), duration=30)

    # If there are active crises, we have a high chance (e.g., 60%) to generate a crisis tweet
    if active_crises and random.random() < 0.6:
        # Weight each active crisis equally so all get signal
        selected = random.choice(list(active_crises.values()))
        return generate_crisis_tweet(selected)
    else:
        return generate_noise_tweet()
