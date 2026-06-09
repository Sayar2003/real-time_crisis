# backend/app/main.py

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.config import (
    SIMULATION_TWEET_RATE,
    ROLLING_WINDOW_MINUTES,
    CRISIS_CATEGORIES
)
from backend.app.simulator import generate_next_tweet, inject_crisis_event
from backend.app.processor import get_classifier, clean_text, geocode_tweet, get_nearest_landmark, reload_spacy
from backend.app.analytics import AnalyticsEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Global queues and states
raw_queue = asyncio.Queue()
processed_queue = asyncio.Queue()

# In-memory database of processed tweets (thread-safe operations in asyncio single loop)
tweets_db: List[dict] = []
active_alerts: List[dict] = []
resolved_alerts: List[dict] = []

# System metrics
total_processed_count = 0
system_start_time = time.time()

# Instantiating the analytics engine
analytics_engine = AnalyticsEngine()

# Pydantic models for request validation
class CrisisInjection(BaseModel):
    category: str
    landmark: str
    duration: int = 30

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrates startup and shutdown processes."""
    # Startup tasks
    logger.info("Initializing AegisStream services...")
    
    # 1. Ensure spaCy is reloaded if installed
    reload_spacy()
    
    # 2. Pre-train NLP classifier
    get_classifier()
    
    # 3. Launch background workers
    sim_worker = asyncio.create_task(simulation_worker())
    proc_worker = asyncio.create_task(processing_worker())
    anal_worker = asyncio.create_task(analytics_worker())
    
    logger.info("AegisStream pipeline workers started.")
    
    yield
    
    # Shutdown tasks
    logger.info("Stopping AegisStream services...")
    sim_worker.cancel()
    proc_worker.cancel()
    anal_worker.cancel()
    
    # Wait for cancel to complete
    await asyncio.gather(sim_worker, proc_worker, anal_worker, return_exceptions=True)
    logger.info("Pipeline workers shut down.")

app = FastAPI(
    title="AegisStream API",
    description="Real-Time Data Streaming and AI-Powered Crisis Intelligence System",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- BACKGROUND WORKER LOOPS ---

async def simulation_worker():
    """Simulates social media ingestion by generating and placing tweets on raw queue."""
    logger.info("Ingestion Simulator started.")
    try:
        while True:
            try:
                raw_tweet = generate_next_tweet()
                await raw_queue.put(raw_tweet)
                await asyncio.sleep(1.0 / SIMULATION_TWEET_RATE)
            except Exception as e:
                logger.error(f"Error generating tweet: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # brief pause then continue
    except asyncio.CancelledError:
        logger.info("Ingestion Simulator stopping.")


async def processing_worker():
    """Consumes raw tweets, cleans, geocodes, classifies, and puts to processed queue."""
    global total_processed_count
    classifier = get_classifier()

    logger.info("Stream Processor started.")
    try:
        while True:
            try:
                raw_tweet = await raw_queue.get()

                # 1. Clean Text
                text = raw_tweet["text"]
                cleaned_text = clean_text(text)

                # 2. Classify Category
                category = classifier.predict(cleaned_text)

                # 3. Geocode (NER or geotag matching)
                lat = raw_tweet["lat"]
                lon = raw_tweet["lon"]
                resolved_landmark = "Unknown"

                if lat is not None and lon is not None:
                    resolved_landmark = get_nearest_landmark(lat, lon)
                else:
                    nlp_lat, nlp_lon, landmark_name = geocode_tweet(text)
                    if nlp_lat is not None and nlp_lon is not None:
                        lat = nlp_lat
                        lon = nlp_lon
                        resolved_landmark = landmark_name

                # 4. Enrich tweet dictionary
                processed_tweet = {
                    "id": raw_tweet["id"],
                    "text": text,
                    "cleaned_text": cleaned_text,
                    "timestamp": raw_tweet["timestamp"],
                    "category": category,
                    "lat": lat,
                    "lon": lon,
                    "landmark": resolved_landmark,
                    "geotagged": raw_tweet["geotagged"] or (lat is not None)
                }

                # 5. Append to recent tweets list
                tweets_db.append(processed_tweet)
                if len(tweets_db) > 1000:
                    tweets_db.pop(0)

                total_processed_count += 1

                # 6. Push to processed queue for analytics
                await processed_queue.put(processed_tweet)
                raw_queue.task_done()

            except Exception as e:
                logger.error(f"Failed to process tweet: {e}", exc_info=True)
                await asyncio.sleep(0.1)  # brief pause then continue
    except asyncio.CancelledError:
        logger.info("Stream Processor stopping.")


async def analytics_worker():
    """Periodically consumes processed tweets, manages rolling window, and runs clustering."""
    global active_alerts, resolved_alerts
    rolling_window: List[dict] = []

    logger.info("Analytics Engine worker started.")
    try:
        while True:
            try:
                await asyncio.sleep(3.0)

                # 1. Drain all processed items currently in queue
                while not processed_queue.empty():
                    processed_tweet = await processed_queue.get()
                    rolling_window.append(processed_tweet)
                    processed_queue.task_done()

                # 2. Prune rolling window
                cutoff_time = time.time() - (ROLLING_WINDOW_MINUTES * 60)
                rolling_window = [t for t in rolling_window if t["timestamp"] >= cutoff_time]

                # 3. Run clustering and anomaly detection
                active_alerts, resolved_alerts = analytics_engine.run_analytics(rolling_window)

            except Exception as e:
                logger.error(f"Error in Analytics Engine: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # brief pause then continue
    except asyncio.CancelledError:
        logger.info("Analytics Engine worker stopping.")


# --- REST API ENDPOINTS ---

@app.get("/api/tweets", response_model=List[dict])
async def get_tweets(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None
):
    """Returns list of recent processed tweets."""
    filtered_tweets = tweets_db
    if category:
        filtered_tweets = [t for t in filtered_tweets if t["category"].lower() == category.lower()]
    return list(reversed(filtered_tweets))[:limit]


@app.get("/api/alerts")
async def get_alerts():
    """Returns active and resolved crisis alerts."""
    return {
        "active": active_alerts,
        "resolved": resolved_alerts
    }


@app.post("/api/inject")
async def inject_crisis(req: CrisisInjection):
    """Triggers custom crisis event inside the stream simulation."""
    if req.category not in CRISIS_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of {CRISIS_CATEGORIES}"
        )
    
    crisis_id = inject_crisis_event(
        category=req.category,
        landmark_name=req.landmark,
        duration=req.duration
    )
    
    logger.info(f"Manual Injection API called: {req.category} at {req.landmark} (id: {crisis_id})")
    return {"status": "success", "crisis_id": crisis_id}


@app.get("/api/status")
async def get_status():
    """Returns operational and performance metrics of AegisStream."""
    uptime = time.time() - system_start_time
    tps = total_processed_count / uptime if uptime > 0 else 0.0
    
    return {
        "status": "operational",
        "uptime_seconds": int(uptime),
        "raw_queue_depth": raw_queue.qsize(),
        "processed_queue_depth": processed_queue.qsize(),
        "total_tweets_processed": total_processed_count,
        "throughput_tps": round(tps, 2),
        "active_alerts_count": len(active_alerts),
        "resolved_alerts_count": len(resolved_alerts)
    }
