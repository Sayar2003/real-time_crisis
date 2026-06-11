# backend/app/simulator.py

import random
import time
import uuid
from typing import Dict, List, Optional
from backend.app.config import CITY_NAME, CITY_ANCHOR, LANDMARKS, CRISIS_CATEGORIES, MONITORED_REGIONS

# Templates for generating synthetic social media posts
BACKGROUND_TEMPLATES = [
    "Enjoying a lovely walk around {landmark} today! #london",
    "Traffic is a bit slow near {landmark} this afternoon.",
    "Having a delicious coffee and a pastry close to {landmark}.",
    "Beautiful weather at {landmark} right now! Perfect for photos.",
    "Shopping near {landmark}, it is incredibly crowded.",
    "Can't wait to check out the amazing view from {landmark}!",
    "Strolling through {landmark} on this nice day.",
    "Just passed by {landmark} on my commute back home.",
    "Met some old friends near {landmark} for a quick lunch.",
    "A lovely, quiet and peaceful evening around {landmark}."
]

CRISIS_TEMPLATES = {
    "Fire": [
        "OMG! Huge fire near {landmark}! Smoke is rising high in the sky! #Emergency",
        "Firefighters are battling a massive blaze at a building near {landmark}! Avoid the area!",
        "There is a serious building fire close to {landmark}. Multiple fire trucks on scene!",
        "Smelling strong smoke and seeing flames near {landmark}. Stay safe everyone!",
        "Building on fire near {landmark}! Fire alarms ringing and people evacuating!"
    ],
    "Flood": [
        "Serious flooding near {landmark}! Roads are completely underwater, stay inside!",
        "The water levels are rising fast around {landmark} after the heavy storm!",
        "Flooded streets close to {landmark}. Traffic is totally blocked and cars are stuck!",
        "Basements getting flooded near {landmark}. This rain is absolutely relentless.",
        "The river is overflowing near {landmark}. Avoid walking near the banks!"
    ],
    "Civic Unrest": [
        "Huge protest blocking the streets near {landmark}! Traffic is at a standstill.",
        "Police and protestors clashing close to {landmark} right now! Heavy tension.",
        "Massive demonstration near {landmark}, riot police are deployed on scene! #protest",
        "Avoid the area around {landmark}, the crowd is getting aggressive and throwing bottles!",
        "Protestors chanting and blocking all major intersections near {landmark}."
    ],
    "Outbreak": [
        "Public health alert: several severe food poisoning cases reported near {landmark}!",
        "A sudden viral outbreak reported at a local school near {landmark}. Health officials warning.",
        "Dozens hospitalized with high fever and infection symptoms close to {landmark}.",
        "Warning: sudden measles outbreak detected in the community around {landmark}.",
        "Many people falling sick near {landmark}. Local clinic is completely full."
    ]
}

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
    if not active_crises and random.random() < 0.05:
        cat = random.choice(CRISIS_CATEGORIES)
        landmark = get_random_landmark()
        inject_crisis_event(cat, landmark, duration=30)
        
    # If there are active crises, we have a high chance (e.g., 60%) to generate a crisis tweet
    if active_crises and random.random() < 0.6:
        crisis_id = random.choice(list(active_crises.keys()))
        return generate_crisis_tweet(active_crises[crisis_id])
    else:
        return generate_noise_tweet()
