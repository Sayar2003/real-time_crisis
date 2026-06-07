# AegisStream: Real-Time Social Media Crisis Signal Detector

AegisStream is a real-time data streaming and AI-powered crisis intelligence system. It monitors simulated social media streams (Twitter/Reddit), cleans and geocodes locations from text, clusters posts semantically and spatially in real-time, and raises live alerts on an interactive Streamlit dashboard.

---

## 🏗️ System Architecture

```
+------------------+     (Raw Tweets)     +-------------------+
| Stream Ingestion | -------------------> | Raw Stream Queue  |
|   (Simulator)    |                      | (asyncio.Queue)   |
+------------------+                      +-------------------+
                                                    |
                                                    v
+------------------+     (Enriched)       +-------------------+
| Processing Worker| <------------------- |  Faust-like loop  |
|  (NLP & Geocode) | -------------------> | Processed Queue   |
+------------------+                      +-------------------+
                                                    |
                                                    v
+------------------+     (Raise Alerts)   +-------------------+
| Analytics Engine | <------------------- | ST-DBSCAN Cluster |
| (Anomaly Alert)  | -------------------> |  & Anomaly Check  |
+------------------+                      +-------------------+
        |
        v
+------------------+     (REST/WebSockets) +------------------+
|  FastAPI Backend | --------------------> | Streamlit App UI |
|  (Shared State)  |                       |  (Pydeck Map)    |
+------------------+                       +------------------+
```

1. **Stream Ingestion (Simulator)**: Generates synthetic posts containing both background noise and localized crisis signals, pushing them into a raw queue.
2. **Stream Processor**: Reads from the raw queue, cleans text, extracts locations via Named Entity Recognition (NER), classifies the crisis category, and pushes to a processed queue.
3. **Analytics Engine (Data Science Core)**: Periodically consumes from the processed queue, runs **Spatio-Temporal DBSCAN** spatial clustering, calculates frequency anomalies (Z-score), and writes alerts to a shared active alert store.
4. **API Gateway (FastAPI)**: Exposes endpoints for processed tweets, active alerts, and manual injection of crises.
5. **Dashboard (Streamlit)**: Polls the backend every 2 seconds, rendering Pydeck WebGL maps, Plotly charts, and allowing users to manually inject custom crises.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.10+** installed.

### 2. Create Virtual Environment
Create and activate a virtual environment:
```powershell
python -m venv .venv
```

To activate on Windows:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
Install the required packages:
```powershell
pip install -r crisis-detector/requirements.txt
```

### 4. Download spaCy NLP Model
Download the small English model for Named Entity Recognition (NER):
```powershell
python -m spacy download en_core_web_sm
```

---

## 🚀 Running the Application

### 1. Start the FastAPI Backend
Launch the API server on port 8000:
```powershell
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
The API documentation will be available at: http://localhost:8000/docs.

### 2. Start the Streamlit Dashboard
In a new terminal window (with the virtual environment activated), launch the frontend:
```powershell
.\.venv\Scripts\streamlit run frontend/dashboard.py
```
The dashboard will open automatically in your browser at: http://localhost:8501.

---

## 🎯 Verification & Testing

1. Once both services are running, open the dashboard. You will see green dots (background tweets) spawning around London.
2. Use the **Manual Crisis Injector** in the sidebar to simulate an event. For example, select **Fire** at **London Eye** and click **Inject Crisis Event**.
3. You will immediately observe:
   - A cluster of orange/red dots appearing around the London Eye on the Pydeck map.
   - A glowing red alert radius circle centered on the epicenter.
   - A red **FIRE ALERT** appearing in the Alerts Inbox with details (Volume, Z-score, Start Time).
   - Injected tweets appearing in the **Live Social Media Stream** feed.
   - Spikes in the "Fire" category on the real-time Plotly trend charts.
4. If no further tweets are injected, the alert will automatically timeout and resolve after 15 seconds.
