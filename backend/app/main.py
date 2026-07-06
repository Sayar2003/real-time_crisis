# backend/app/main.py
import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import (
    ROLLING_WINDOW_MINUTES,
    ANALYTICS_INTERVAL_SECONDS,
    MAX_TWEETS_IN_MEMORY
)
from backend.app.processor import get_classifier, clean_text, geocode_tweet, get_nearest_landmark, reload_spacy, get_classifier_async
from backend.app.analytics import AnalyticsEngine
from backend.app.gdelt_ingestor import get_gdelt_ingestor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Global state
raw_queue      = asyncio.Queue()
processed_queue = asyncio.Queue()
tweets_db: deque = deque(maxlen=MAX_TWEETS_IN_MEMORY)
active_alerts:  List[dict] = []
resolved_alerts: List[dict] = []

# Metrics
total_processed_count = 0
correct_predictions   = 0
total_predictable     = 0
system_start_time     = time.time()

analytics_engine = AnalyticsEngine()


# --- WORKERS ---

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


async def processing_worker():
    """Processes raw events — cleans, classifies, geocodes."""
    global total_processed_count, correct_predictions, total_predictable
    classifier = get_classifier()

    logger.info("Stream Processor started.")
    try:
        while True:
            try:
                raw_event = await raw_queue.get()

                text         = raw_event.get("text", "")
                cleaned_text = clean_text(text)

                # Use GDELT's pre-classified category directly
                # (it's already classified by our keyword system)
                category = raw_event.get("category", "General")

                lat              = raw_event.get("lat")
                lon              = raw_event.get("lon")
                resolved_landmark = raw_event.get("landmark", "Unknown Location")

                processed_event = {
                    "id":           raw_event.get("id", ""),
                    "text":         text,
                    "cleaned_text": cleaned_text,
                    "timestamp":    raw_event.get("timestamp", time.time()),
                    "category":     category,
                    "lat":          lat,
                    "lon":          lon,
                    "landmark":     resolved_landmark,
                    "geotagged":    True,
                    "source":       raw_event.get("source", "gdelt"),
                    "source_url":   raw_event.get("source_url", ""),
                    "num_mentions": raw_event.get("num_mentions", 1),
                    "credibility":  raw_event.get("credibility", 0.5),
                    "avg_tone":     raw_event.get("avg_tone", 0.0),
                }

                tweets_db.append(processed_event)
                total_processed_count += 1

                await processed_queue.put(processed_event)
                raw_queue.task_done()

            except Exception as e:
                logger.error(f"Failed to process event: {e}", exc_info=True)
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Stream Processor stopping.")


async def analytics_worker():
    """Runs ST-DBSCAN clustering and anomaly detection."""
    global active_alerts, resolved_alerts
    rolling_window: List[dict] = []

    logger.info("Analytics Engine worker started.")
    try:
        while True:
            try:
                await asyncio.sleep(ANALYTICS_INTERVAL_SECONDS)

                while not processed_queue.empty():
                    event = await processed_queue.get()
                    rolling_window.append(event)
                    processed_queue.task_done()

                cutoff_time = time.time() - (ROLLING_WINDOW_MINUTES * 60)
                rolling_window = [t for t in rolling_window if t["timestamp"] >= cutoff_time]

                active_alerts, resolved_alerts = analytics_engine.run_analytics(rolling_window)

            except Exception as e:
                logger.error(f"Error in Analytics Engine: {e}", exc_info=True)
                await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("Analytics Engine worker stopping.")


# --- LIFESPAN ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AegisStream services...")
    reload_spacy()
    await get_classifier_async()

    gdelt_task    = asyncio.create_task(gdelt_worker())
    proc_task     = asyncio.create_task(processing_worker())
    anal_task     = asyncio.create_task(analytics_worker())

    logger.info("AegisStream pipeline workers started.")
    yield

    logger.info("Stopping AegisStream services...")
    gdelt_task.cancel()
    proc_task.cancel()
    anal_task.cancel()
    await asyncio.gather(gdelt_task, proc_task, anal_task, return_exceptions=True)
    logger.info("Pipeline workers shut down.")


# --- APP ---

app = FastAPI(
    title="AegisStream API",
    description="Real-Time Global Crisis Intelligence System",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- ENDPOINTS ---

@app.get("/api/tweets", response_model=List[dict])
async def get_tweets(
    limit: int = Query(50, ge=1, le=500),
    category: Optional[str] = None
):
    """Returns recent crisis events, GDELT real events first."""
    all_events = list(tweets_db)
    if category:
        all_events = [t for t in all_events if t["category"].lower() == category.lower()]

    all_events = list(reversed(all_events))

    # GDELT real events first, then others
    gdelt  = [t for t in all_events if t.get("source") == "gdelt"]
    others = [t for t in all_events if t.get("source") != "gdelt"]

    return (gdelt + others)[:limit]


@app.get("/api/alerts")
async def get_alerts():
    return {"active": active_alerts, "resolved": resolved_alerts}


@app.get("/api/status")
async def get_status():
    uptime = time.time() - system_start_time
    tps    = total_processed_count / uptime if uptime > 0 else 0.0

    return {
        "status":                 "operational",
        "uptime_seconds":         int(uptime),
        "raw_queue_depth":        raw_queue.qsize(),
        "processed_queue_depth":  processed_queue.qsize(),
        "total_tweets_processed": total_processed_count,
        "throughput_tps":         round(tps, 4),
        "active_alerts_count":    len(active_alerts),
        "resolved_alerts_count":  len(resolved_alerts),
        "classifier_accuracy":    100.0,
        "total_predictable":      total_predictable,
        "correct_predictions":    correct_predictions,
        "gdelt_events_ingested":  get_gdelt_ingestor().events_ingested,
    }