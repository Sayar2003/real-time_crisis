# AegisStream — Developer Log

## June 7, 2026 — Project Setup
- Created GitHub repository
- Designed FastAPI + asyncio pipeline architecture
- Set up SQLite schema and project folder structure

## June 8-9, 2026 — Core Pipeline
- Built stream simulator for testing
- Implemented asyncio.Queue-based three-worker system
- Simulator → Processor → Analytics workers
- Added graceful shutdown with CancelledError handling

## June 10-11, 2026 — NLP Classifier
- Integrated spaCy NER for geo-location extraction
- Replaced TF-IDF + Naive Bayes with zero-shot BART transformer
- Added confidence threshold and keyword fallback
- Classifier accuracy tracking via true_category comparison

## June 12-13, 2026 — Anomaly Detection
- Implemented ST-DBSCAN spatio-temporal clustering
- Built Z-score anomaly detector with 30-min rolling baseline
- Added cold-start protection (min 5 baseline bins)
- Fixed NaN coordinate validation for DBSCAN

## June 14, 2026 — Multi-City + GDELT
- Integrated GDELT real-world event ingestion
- GDELT polls every 15 minutes — no API key required
- Expanded from 4 cities to global coverage

## June 15, 2026 — LLM + Notifications
- Integrated Groq API (Llama 3 70B) for alert summaries
- Built Slack webhook notification system
- Added Telegram bot notifications
- Alerts generate 3-sentence AI briefings automatically

## June 16-17, 2026 — Dashboard Polish
- Complete CSS redesign with Inter + JetBrains Mono fonts
- Animated top accent bar and metric pulse animations
- HeatmapLayer added to Pydeck map
- Dynamic map centroid based on active alert locations
- Real-time classifier accuracy metric

## June 18-20, 2026 — Interactive Features
- Category filter pills for live feed
- Feed keyword search bar
- Alert countdown timer with color-coded urgency
- Glowing hover effects on buttons

## June 28-30, 2026 — Real Data Overhaul
- Removed all simulated data — 100% real data pipeline
- Expanded to 12 crisis categories
- Added OpenWeatherMap severe weather integration
- Added NewsAPI real headline integration
- Added crisis severity scoring engine (1-10 scale)
- Feed deduplication by text content
- GDELT events shown first in feed

## July 7, 2026 — Final Features
- Added Windy.com live storm visualization embed
- Added hourly crisis event timeline chart
- Added severity badges on feed cards
- Added clickable source URL links
- Global heatmap showing hotspots worldwide
- 3 independent real data sources fully operational
- Final README update with screenshots