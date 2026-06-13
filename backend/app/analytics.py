# backend/app/analytics.py

import time
import logging
import math
import asyncio
from collections import deque
from typing import List, Dict, Tuple, Optional
import numpy as np
from sklearn.cluster import DBSCAN

from backend.app.config import (
    DBSCAN_EPS,
    DBSCAN_MIN_SAMPLES,
    TEMPORAL_EPS_MINUTES,
    ANOMALY_Z_SCORE_THRESHOLD,
    MIN_ALERT_SIZE,
    HISTORICAL_WINDOW_MINUTES,
    CRISIS_CATEGORIES,
    ACTIVE_ALERT_TIMEOUT_SECONDS
)

logger = logging.getLogger(__name__)

class AnomalyTracker:
    """Tracks historical volume of crisis categories in 1-minute bins to compute Z-scores."""
    def __init__(self, window_size: int = HISTORICAL_WINDOW_MINUTES):
        self.window_size = window_size
        # Initialize history for each crisis category with zeros
        self.history: Dict[str, deque] = {
        cat: deque([0] * window_size, maxlen=window_size)
        for cat in CRISIS_CATEGORIES
   }
        self.last_bin_time = time.time()

    def update(self, tweets: List[dict]):
        """Updates the historical bins. Slides the window if a minute has passed."""
        now = time.time()
        elapsed = now - self.last_bin_time

        if elapsed >= 60.0:
            bins_to_slide = min(int(elapsed // 60.0), self.window_size)
            # advance last_bin_time by the number of whole minutes slid
            self.last_bin_time += bins_to_slide * 60.0

            for cat in CRISIS_CATEGORIES:
                recent_count = sum(
                    1 for t in tweets
                    if t.get("category") == cat and now - t.get("timestamp", 0) <= 60.0
                )

                # Fill missed bins with zeros, append current count last
                for i in range(bins_to_slide):
                    if i < bins_to_slide - 1:
                        self.history[cat].append(0)       # missed bins = no activity
                    else:
                        self.history[cat].append(recent_count)  # current bin
                # deque(maxlen) auto-drops oldest — no pop(0) needed

    def calculate_z_score(self, category: str, count: int) -> float:
        if category not in self.history:
            return 0.0

        counts = list(self.history[category])

        # Require at least 5 non-zero bins before trusting the baseline
        # Prevents false alerts firing immediately on cold start
        non_zero_bins = sum(1 for c in counts if c > 0)
        if non_zero_bins < 5:
            return 0.0

        mean = np.mean(counts)
        std = max(np.std(counts), 0.5)   # floor at 0.5 to avoid division by near-zero
        return float((count - mean) / std)


class AnalyticsEngine:
    """Performs Spatio-Temporal DBSCAN and anomaly detection over a rolling window of tweets."""
    def __init__(self):
        self.anomaly_tracker = AnomalyTracker()
        self.active_alerts: Dict[str, dict] = {}
        self.resolved_alerts: List[dict] = []
        self.alert_id_counter = 1
    def _extract_landmark(self, cluster_tweets: list) -> str:
        """Returns the most common landmark mentioned across cluster tweets."""
        landmarks = [
            t.get("landmark", "") 
            for t in cluster_tweets 
            if t.get("landmark", "") not in ("", "Unknown", None)
        ]
        if not landmarks:
            return "Unknown Location"
        return max(set(landmarks), key=landmarks.count)

    def run_analytics(self, rolling_tweets: List[dict]) -> Tuple[List[dict], List[dict]]:
        """
        Executes ST-DBSCAN clustering and Z-score anomaly check.
        Updates active alerts and returns (active_alerts_list, resolved_alerts_list).
        """
        # 1. Update historical counts for Z-score baseline
        self.anomaly_tracker.update(rolling_tweets)
        
        # 2. Filter tweets with coordinates and crisis categories
        crisis_tweets = [
            t for t in rolling_tweets
            if t.get("lat") is not None and t.get("lon") is not None and t.get("category") in CRISIS_CATEGORIES
        ]
        
        detected_clusters = []
        
        if len(crisis_tweets) >= DBSCAN_MIN_SAMPLES:
            # Build 3D feature array [lat, lon, time_scaled]
            # Scale factor converts time (in minutes) to be comparable with coordinates in degrees
            scale_factor = DBSCAN_EPS / TEMPORAL_EPS_MINUTES
            
            features = []
            for t in crisis_tweets:
                t_min = t["timestamp"] / 60.0
                t_scaled = t_min * scale_factor
                features.append([t["lat"], t["lon"], t_scaled])
                
            X = np.array(features)
            
            # Run DBSCAN
            db = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
            labels = db.fit_predict(X)
            
            # Extract clusters
            unique_labels = set(labels)
            for label in unique_labels:
                if label == -1:
                    continue  # Ignore noise
                    
                cluster_indices = np.where(labels == label)[0]
                cluster_tweets = [crisis_tweets[i] for i in cluster_indices]
                
                # Compute centroid (epicenter)
                lats = [t["lat"] for t in cluster_tweets]
                lons = [t["lon"] for t in cluster_tweets]
                lat_center = float(np.mean(lats))
                lon_center = float(np.mean(lons))
                
                # Determine majority category in cluster
                categories = [t["category"] for t in cluster_tweets]
                majority_category = max(set(categories), key=categories.count)
                
                detected_clusters.append({
                    "category": majority_category,
                    "lat": lat_center,
                    "lon": lon_center,
                    "tweets": cluster_tweets,
                    "count": len(cluster_tweets)
                })
                
        # 3. Process clusters and update alerts database
        current_time = time.time()
        matched_alert_ids = set()
        
        for cluster in detected_clusters:
            category = cluster["category"]
            lat = cluster["lat"]
            lon = cluster["lon"]
            count = cluster["count"]
            cluster_tweets = cluster["tweets"]
            
            # Compute Z-score anomaly metric
            z_score = self.anomaly_tracker.calculate_z_score(category, count)
            
            # Check if this qualifies as an anomaly alert
            if z_score >= ANOMALY_Z_SCORE_THRESHOLD and count >= MIN_ALERT_SIZE:
                # Check if matches an existing active alert spatially (same category and within EPS distance)
                matched_id = None
                for aid, alert in self.active_alerts.items():
                    if alert["category"] == category:
                        dist = math.sqrt((lat - alert["lat"])**2 + (lon - alert["lon"])**2)
                        if dist <= DBSCAN_EPS * 1.5:
                            matched_id = aid
                            break
                            
                if matched_id:
                    # Update existing alert
                    alert = self.active_alerts[matched_id]
                    alert["lat"] = lat
                    alert["lon"] = lon
                    alert["tweet_count"] = count
                    alert["tweets"] = cluster_tweets
                    alert["z_score"] = z_score
                    alert["landmark"] = self._extract_landmark(cluster_tweets)  # ← add this line
                    alert["last_updated"] = current_time
                    matched_alert_ids.add(matched_id)
                else:
                  # Create new alert
                  alert_id = f"ALERT-{self.alert_id_counter}"
                  self.alert_id_counter += 1

                  landmark = self._extract_landmark(cluster_tweets)

                  self.active_alerts[alert_id] = {
                  "id": alert_id,
                  "category": category,
                  "lat": lat,
                  "lon": lon,
                  "tweet_count": count,
                  "tweets": cluster_tweets,
                  "z_score": z_score,
                  "landmark": landmark,
                  "status": "Active",
                  "start_time": current_time,
                  "last_updated": current_time
                }
                matched_alert_ids.add(alert_id)
                logger.info(f"🚨 NEW ALERT RAISED: {alert_id} ({category}) at ({lat:.4f}, {lon:.4f}) | Landmark: {landmark} | Z-score {z_score:.2f}")

                # Schedule Groq LLM summary generation (non-blocking thread)
                asyncio.create_task(self._attach_llm_summary(alert_id))

        # 4. Handle timeouts and resolve inactive alerts
        resolved_keys = []
        for aid, alert in list(self.active_alerts.items()):
            # Resolve if it wasn't matched in this run AND has timed out since last update
            if aid not in matched_alert_ids and (current_time - alert["last_updated"] > ACTIVE_ALERT_TIMEOUT_SECONDS):
                alert["status"] = "Resolved"
                alert["resolved_time"] = current_time
                self.resolved_alerts.append(alert)
                resolved_keys.append(aid)
                logger.info(f"✅ ALERT RESOLVED: {aid} ({alert['category']})")
                
        for aid in resolved_keys:
            self.active_alerts.pop(aid)
            
        # Keep resolved alerts list size capped to avoid memory growth
        if len(self.resolved_alerts) > 50:
            self.resolved_alerts = self.resolved_alerts[-50:]
            
        return list(self.active_alerts.values()), self.resolved_alerts


async def _attach_llm_summary(self, alert_id: str):
    """Generates LLM summary, attaches it to alert, and sends Slack notification."""
    try:
        from backend.app.llm import generate_alert_summary
        from backend.app.notifier import send_slack_alert

        alert = self.active_alerts.get(alert_id)
        if alert is None:
            return

        # Generate LLM summary
        summary = await generate_alert_summary(alert)

        # Attach to alert
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]["llm_summary"] = summary
            logger.info(f"LLM summary attached to {alert_id}")

        # Send Slack notification with summary
        await send_slack_alert(alert, llm_summary=summary)

    except Exception as e:
        logger.error(f"Failed to attach LLM summary or send Slack for {alert_id}: {e}")