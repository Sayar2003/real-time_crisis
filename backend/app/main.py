# backend/app/main.py
import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.config import (
    SIMULATION_TWEET_RATE,
    ROLLING_WINDOW_MINUTES,
    CRISIS_CATEGORIES,
    ANALYTICS_INTERVAL_SECONDS,
    MAX_TWEETS_IN_MEMORY
)
from backend.app.simulator import generate_next_tweet, inject_crisis_event
from backend.app.processor import get_classifier, clean_text, geocode_tweet, get_nearest_landmark, reload_spacy
from backend.app.analytics import AnalyticsEngine
from backend.app.gdelt_ingestor import get_gdelt_ingestor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Global queues and states
raw_queue = asyncio.Queue()
processed_queue = asyncio.Queue()

# In-memory database of processed tweets — deque auto-drops oldest at maxlen
tweets_db: deque = deque(maxlen=MAX_TWEETS_IN_MEMORY)
active_alerts: List[dict] = []
resolved_alerts: List[dict] = []

# System metrics
total_processed_count = 0
system_start_time = time.time()

# Classifier accuracy tracking
correct_predictions = 0
total_predictable   = 0

# Analytics engine
analytics_engine = AnalyticsEngine()

# Pydantic models
class CrisisInjection(BaseModel):
    category: str
    landmark: str
    duration: int = 30


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
                await asyncio.sleep(1.0)
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

                # 3. Geocode
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

                # 4. Enrich tweet
                processed_tweet = {
                    "id":        raw_tweet["id"],
                    "text":      text,
                    "cleaned_text": cleaned_text,
                    "timestamp": raw_tweet["timestamp"],
                    "category":  category,
                    "lat":       lat,
                    "lon":       lon,
                    "landmark":  resolved_landmark,
                    "geotagged": raw_tweet.get("geotagged", False) or (lat is not None),
                    "source":    raw_tweet.get("source", "simulator"),
                }

                # 5. Store
                tweets_db.append(processed_tweet)
                total_processed_count += 1

                # 6. Track classifier accuracy using simulator ground truth
                true_cat = raw_tweet.get("true_category")
                if true_cat and true_cat != "General":
                    global correct_predictions, total_predictable
                    total_predictable += 1
                    if category == true_cat:
                        correct_predictions += 1

                # 6. Push to analytics queue
                await processed_queue.put(processed_tweet)
                raw_queue.task_done()

            except Exception as e:
                logger.error(f"Failed to process tweet: {e}", exc_info=True)
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Stream Processor stopping.")


async def analytics_worker():
    """Periodically runs clustering and anomaly detection on rolling window."""
    global active_alerts, resolved_alerts
    rolling_window: List[dict] = []

    logger.info("Analytics Engine worker started.")
    try:
        while True:
            try:
                await asyncio.sleep(ANALYTICS_INTERVAL_SECONDS)

                while not processed_queue.empty():
                    processed_tweet = await processed_queue.get()
                    rolling_window.append(processed_tweet)
                    processed_queue.task_done()

                cutoff_time = time.time() - (ROLLING_WINDOW_MINUTES * 60)
                rolling_window = [t for t in rolling_window if t["timestamp"] >= cutoff_time]

                active_alerts, resolved_alerts = analytics_engine.run_analytics(rolling_window)

            except Exception as e:
                logger.error(f"Error in Analytics Engine: {e}", exc_info=True)
                await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("Analytics Engine worker stopping.")


async def gdelt_worker():
    """Polls GDELT every 15 minutes for real-world crisis events."""
    ingestor = get_gdelt_ingestor()
    logger.info("GDELT Ingestor started — polling every 15 minutes.")
    try:
        while True:
            try:
                loop = asyncio.get_event_loop()
                events = await loop.run_in_executor(None, ingestor.fetch_latest)

                for event in events:
                    await raw_queue.put(event)

                logger.info(f"GDELT: {len(events)} events added to pipeline.")

            except Exception as e:
                logger.error(f"GDELT worker error: {e}", exc_info=True)

            await asyncio.sleep(900)

    except asyncio.CancelledError:
        logger.info("GDELT Ingestor stopping.")


# --- LIFESPAN ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrates startup and shutdown processes."""
    logger.info("Initializing AegisStream services...")

    reload_spacy()

    from backend.app.processor import get_classifier_async
    await get_classifier_async()

    sim_worker        = asyncio.create_task(simulation_worker())
    proc_worker       = asyncio.create_task(processing_worker())
    anal_worker       = asyncio.create_task(analytics_worker())
    gdelt_worker_task = asyncio.create_task(gdelt_worker())

    logger.info("AegisStream pipeline workers started.")

    yield

    logger.info("Stopping AegisStream services...")
    sim_worker.cancel()
    proc_worker.cancel()
    anal_worker.cancel()
    gdelt_worker_task.cancel()
    await asyncio.gather(
        sim_worker, proc_worker, anal_worker, gdelt_worker_task,
        return_exceptions=True
    )
    logger.info("Pipeline workers shut down.")


# --- APP ---

app = FastAPI(
    title="AegisStream API",
    description="Real-Time Data Streaming and AI-Powered Crisis Intelligence System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST API ENDPOINTS ---

@app.get("/api/tweets", response_model=List[dict])
async def get_tweets(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None
):
    all_tweets = list(tweets_db)
    if category:
        all_tweets = [t for t in all_tweets if t["category"].lower() == category.lower()]
    return list(reversed(all_tweets))[:limit]


@app.get("/api/alerts")
async def get_alerts():
    return {
        "active": active_alerts,
        "resolved": resolved_alerts
    }


@app.post("/api/inject")
async def inject_crisis(req: CrisisInjection):
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
    uptime = time.time() - system_start_time
    tps = total_processed_count / uptime if uptime > 0 else 0.0
    accuracy = (correct_predictions / total_predictable * 100) if total_predictable > 0 else 0.0

    return {
        "status":                   "operational",
        "uptime_seconds":           int(uptime),
        "raw_queue_depth":          raw_queue.qsize(),
        "processed_queue_depth":    processed_queue.qsize(),
        "total_tweets_processed":   total_processed_count,
        "throughput_tps":           round(tps, 2),
        "active_alerts_count":      len(active_alerts),
        "resolved_alerts_count":    len(resolved_alerts),
        "classifier_accuracy":      round(accuracy, 1),
        "total_predictable":        total_predictable,
        "correct_predictions":      correct_predictions,
    }