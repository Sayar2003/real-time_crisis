# frontend/dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from streamlit_autorefresh import st_autorefresh
import pydeck as pdk
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AegisStream Dashboard",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- BACKEND CONNECTION ---
BACKEND_URL = "http://localhost:8000"

# --- CUSTOM CSS STYLING ---
st.markdown("""
<style>
    /* Dark dashboard theme styling */
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
    }
    
    /* Title header style */
    .dashboard-title {
        color: #66fcf1;
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0px;
        text-shadow: 0 0 10px rgba(102, 252, 241, 0.3);
    }
    
    .dashboard-subtitle {
        color: #45f3ff;
        font-size: 0.95rem;
        margin-top: 0px;
        margin-bottom: 20px;
        opacity: 0.8;
    }
    
    /* Scrollable feed container */
    .feed-container {
        max-height: 550px;
        overflow-y: auto;
        padding-right: 5px;
    }
    
    /* Tweet Card Styling */
    .tweet-card {
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        background-color: #1f2833;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease;
    }
    .tweet-card:hover {
        transform: translateY(-2px);
    }
    
    .tweet-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 6px;
    }
    
    .category-badge {
        font-weight: bold;
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 4px;
        color: #ffffff;
    }
    
    .badge-general { background-color: #7f8c8d; }
    .badge-fire { background-color: #e74c3c; box-shadow: 0 0 5px rgba(231, 76, 60, 0.5); }
    .badge-flood { background-color: #3498db; box-shadow: 0 0 5px rgba(52, 152, 219, 0.5); }
    .badge-unrest { background-color: #f1c40f; color: #000000; box-shadow: 0 0 5px rgba(241, 196, 15, 0.5); }
    .badge-outbreak { background-color: #9b59b6; box-shadow: 0 0 5px rgba(155, 89, 182, 0.5); }
    
    .landmark-tag {
        color: #66fcf1;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .tweet-time {
        color: #a0a0b0;
        font-size: 0.72rem;
    }
    
    .tweet-text {
        margin: 0;
        color: #e0e0e0;
        font-size: 0.82rem;
        line-height: 1.35;
    }
    
    /* Metric styling */
    .metric-box {
        background-color: #1f2833;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        border: 1px solid #1f2833;
    }
    .metric-value-critical {
        color: #e74c3c;
        font-size: 2rem;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(231, 76, 60, 0.3);
    }
    .metric-value-warning {
        color: #f1c40f;
        font-size: 2rem;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(241, 196, 15, 0.3);
    }
    .metric-value-ok {
        color: #2ecc71;
        font-size: 2rem;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(46, 204, 113, 0.3);
    }
    .metric-value-info {
        color: #66fcf1;
        font-size: 2rem;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(102, 252, 241, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- REFRESH CONFIG ---
# Autorefresh the dashboard every 2 seconds to poll FastAPI backend
st_refresh = st_autorefresh(interval=2000, key="data_refresh_trigger")

# --- DATA POLLING HELPERS ---
def fetch_tweets():
    try:
        response = requests.get(f"{BACKEND_URL}/api/tweets?limit=100")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

def fetch_alerts():
    try:
        response = requests.get(f"{BACKEND_URL}/api/alerts")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"active": [], "resolved": []}

def fetch_status():
    try:
        response = requests.get(f"{BACKEND_URL}/api/status")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def trigger_injection(category, landmark, duration=30):
    try:
        payload = {"category": category, "landmark": landmark, "duration": duration}
        response = requests.post(f"{BACKEND_URL}/api/inject", json=payload)
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Injection failed: {e}")
    return False

# --- STATE LOAD ---
status_data = fetch_status()
tweets_data = fetch_tweets()
alerts_data = fetch_alerts()

# --- BACKEND OFFLINE SCREEN ---
if status_data is None:
    st.markdown("<h1 class='dashboard-title'>🚨 AegisStream crisis detector</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#e74c3c;'>Backend API Server is Offline</h4>", unsafe_allow_html=True)
    st.info("""
    **To start the backend pipeline, please run the following command in a terminal:**
    ```powershell
    .\\.venv\\Scripts\\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
    ```
    """)
    st.stop()

# --- APP LAYOUT ---

# Header section
st.markdown("<div class='dashboard-title'>🛡️ AegisStream Crisis Intelligence</div>", unsafe_allow_html=True)
st.markdown("<div class='dashboard-subtitle'>Real-Time Data Streaming & Spatial-Temporal Anomaly Detector</div>", unsafe_allow_html=True)

# Metrics Grid
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

active_cnt = len(alerts_data["active"])
throughput = status_data["throughput_tps"]
total_processed = status_data["total_tweets_processed"]

# Calculate dynamic alert state
if active_cnt >= 3:
    status_label = "CRITICAL CRISIS ALERT"
    status_class = "metric-value-critical"
elif active_cnt >= 1:
    status_label = "ACTIVE WARNINGS"
    status_class = "metric-value-warning"
else:
    status_label = "STREAM MONITORING"
    status_class = "metric-value-ok"

with m_col1:
    st.markdown(f"""
    <div class='metric-box'>
        <div style='font-size:0.75rem; color:#a0a0b0; text-transform:uppercase;'>System Alert Level</div>
        <div class='{status_class}'>{status_label}</div>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
    <div class='metric-box'>
        <div style='font-size:0.75rem; color:#a0a0b0; text-transform:uppercase;'>Active Event Clusters</div>
        <div class='metric-value-info'>{active_cnt}</div>
    </div>
    """, unsafe_allow_html=True)

with m_col3:
    st.markdown(f"""
    <div class='metric-box'>
        <div style='font-size:0.75rem; color:#a0a0b0; text-transform:uppercase;'>Pipeline Throughput</div>
        <div class='metric-value-info'>{throughput:.1f} <span style='font-size:0.9rem;'>tweets/s</span></div>
    </div>
    """, unsafe_allow_html=True)

with m_col4:
    st.markdown(f"""
    <div class='metric-box'>
        <div style='font-size:0.75rem; color:#a0a0b0; text-transform:uppercase;'>Total Streams Processed</div>
        <div class='metric-value-info'>{total_processed}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Split Layout: Left (Map & Charts) / Right (Feed)
col_left, col_right = st.columns([0.65, 0.35])

with col_left:
    st.markdown("### 🗺️ Spatio-Temporal Event Episenters")
    
    # Coordinates of tweets for scatter layer
    tweets_list = []
    for t in tweets_data:
        if t["lat"] is not None and t["lon"] is not None:
            # Color coding by category
            cat = t["category"]
            if cat == "Fire":
                color = [231, 76, 60, 180] # Red
            elif cat == "Flood":
                color = [52, 152, 219, 180] # Blue
            elif cat == "Civic Unrest":
                color = [241, 196, 15, 180] # Yellow
            elif cat == "Outbreak":
                color = [155, 89, 182, 180] # Purple
            else:
                color = [46, 204, 113, 100] # Green (General)
                
            tweets_list.append({
                "lat": t["lat"],
                "lon": t["lon"],
                "category": cat,
                "landmark": t["landmark"],
                "color": color
            })
            
    df_tweets = pd.DataFrame(tweets_list) if tweets_list else pd.DataFrame(columns=["lat", "lon", "category", "landmark", "color"])
    
    # Active alerts coordinates for alert range rings
    alerts_list = []
    for a in alerts_data["active"]:
        alerts_list.append({
            "lat": a["lat"],
            "lon": a["lon"],
            "category": a["category"],
            "tweet_count": a["tweet_count"],
            "z_score": a["z_score"]
        })
    df_alerts = pd.DataFrame(alerts_list) if alerts_list else pd.DataFrame(columns=["lat", "lon", "category", "tweet_count", "z_score"])
    
    # Pydeck Dark Maps configuration
    tweets_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_tweets,
        get_position="[lon, lat]",
        get_color="color",
        get_radius=80,
        pickable=True
    )
    
    # Glowing orange/red alert epicenters
    alerts_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_alerts,
        get_position="[lon, lat]",
        get_color="[231, 76, 60, 60]", # Red glow fill
        get_line_color="[231, 76, 60, 255]", # Solid red perimeter
        line_width_min_pixels=2,
        get_radius=600, # 600m radius
        pickable=True
    )
    
    view_state = pdk.ViewState(
        latitude=51.5074,
        longitude=-0.1278,
        zoom=11.8,
        pitch=30
    )
    
    tooltip = {
        "html": "<b>Category:</b> {category}<br/><b>Landmark:</b> {landmark}",
        "style": {"background-color": "#1f2833", "color": "#ffffff"}
    }
    
    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/dark-v10",
            initial_view_state=view_state,
            layers=[tweets_layer, alerts_layer],
            tooltip=tooltip
        )
    )
    
    # Plotly Timeline and distributions
    st.markdown("### 📊 Real-Time Stream Analytics")
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        if len(tweets_data) > 0:
            df_chart = pd.DataFrame(tweets_data)
            df_chart['datetime'] = pd.to_datetime(df_chart['timestamp'], unit='s')
            df_chart['time_bin'] = df_chart['datetime'].dt.floor('10s') # 10s intervals
            
            # Count by interval and category
            grouped = df_chart.groupby(['time_bin', 'category']).size().unstack(fill_value=0).reset_index()
            
            # Ensure columns present
            for c in ["General", "Fire", "Flood", "Civic Unrest", "Outbreak"]:
                if c not in grouped.columns:
                    grouped[c] = 0
                    
            melted = grouped.melt(id_vars=['time_bin'], value_vars=["General", "Fire", "Flood", "Civic Unrest", "Outbreak"],
                                  var_name='Category', value_name='Volume')
            
            fig_line = px.line(
                melted,
                x='time_bin',
                y='Volume',
                color='Category',
                color_discrete_map={
                    "General": "#2ecc71",
                    "Fire": "#e74c3c",
                    "Flood": "#3498db",
                    "Civic Unrest": "#f1c40f",
                    "Outbreak": "#9b59b6"
                },
                title="Historical Signal Trends (10s Bins)",
                template="plotly_dark"
            )
            fig_line.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=250,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
    with c_chart2:
        if len(tweets_data) > 0:
            df_cat = pd.DataFrame(tweets_data)
            counts = df_cat['category'].value_counts().reset_index()
            counts.columns = ['Category', 'Volume']
            
            fig_bar = px.bar(
                counts,
                x='Category',
                y='Volume',
                color='Category',
                color_discrete_map={
                    "General": "#2ecc71",
                    "Fire": "#e74c3c",
                    "Flood": "#3498db",
                    "Civic Unrest": "#f1c40f",
                    "Outbreak": "#9b59b6"
                },
                title="Total Stream Volume by Category",
                template="plotly_dark"
            )
            fig_bar.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=250, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown("### 🔔 Active Alerts Inbox")
    if len(alerts_data["active"]) == 0:
        st.info("No active crisis events detected.")
    else:
        for a in alerts_data["active"]:
            st.error(f"""
            🔴 **{a['category'].upper()} ALERT ({a['id']})**
            * **Epicenter:** {a['tweets'][0]['landmark']} (lat: {a['lat']:.4f}, lon: {a['lon']:.4f})
            * **Volume:** {a['tweet_count']} clustered reports
            * **Signal Z-score:** {a['z_score']:.2f} (anomaly threshold exceeded)
            * **Active since:** {time.strftime('%H:%M:%S', time.localtime(a['start_time']))}
            """)
            
    st.write("")
    
    st.markdown("### 💬 Live Social media stream")
    feed_html = "<div class='feed-container'>"
    
    if len(tweets_data) == 0:
        feed_html += "<p style='color:#a0a0b0; font-size:0.85rem;'>Waiting for social media stream ingestion...</p>"
    else:
        for t in tweets_data[:30]:  # Top 30 tweets
            cat = t["category"]
            badge_class = "badge-general"
            if cat == "Fire":
                badge_class = "badge-fire"
            elif cat == "Flood":
                badge_class = "badge-flood"
            elif cat == "Civic Unrest":
                badge_class = "badge-unrest"
            elif cat == "Outbreak":
                badge_class = "badge-outbreak"
                
            landmark = t["landmark"]
            t_time = time.strftime("%H:%M:%S", time.localtime(t["timestamp"]))
            
            feed_html += f"""
            <div class='tweet-card'>
                <div class='tweet-header'>
                    <span class='category-badge {badge_class}'>{cat.upper()}</span>
                    <span class='landmark-tag'>📍 {landmark}</span>
                    <span class='tweet-time'>{t_time}</span>
                </div>
                <p class='tweet-text'>{t['text']}</p>
            </div>
            """
            
    feed_html += "</div>"
    st.markdown(feed_html, unsafe_allow_html=True)


# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("<h2 style='color:#66fcf1;'>⚙️ AegisStream Control Panel</h2>", unsafe_allow_html=True)
st.sidebar.write(f"**Backend Status:** Operational (Uptime: {status_data['uptime_seconds']}s)")
st.sidebar.write(f"**Simulated Queue Depth:** {status_data['raw_queue_depth']} raw posts")

st.sidebar.divider()

# Configuration Parameter Readouts
st.sidebar.markdown("#### Analytics Engine Parameters")
st.sidebar.markdown(f"- **DBSCAN Epsilon (Spatial):** `0.01` (~1.1 km)")
st.sidebar.markdown(f"- **DBSCAN Min Samples:** `4` tweets")
st.sidebar.markdown(f"- **ST-DBSCAN Temporal Window:** `3.0` minutes")
st.sidebar.markdown(f"- **Anomaly Z-score Threshold:** `3.0` standard deviations")

st.sidebar.divider()

# Crisis Injector
st.sidebar.markdown("### 🚀 Manual Crisis Injector")
st.sidebar.write("Simulate a localized crisis signal event at a London landmark:")

inject_cat = st.sidebar.selectbox("Crisis Category", ["Fire", "Flood", "Civic Unrest", "Outbreak"])
inject_landmark = st.sidebar.selectbox("Epicenter Landmark", [
    "Big Ben", "Hyde Park", "London Eye", "Tower Bridge", "Buckingham Palace", 
    "Trafalgar Square", "British Museum", "Soho", "Covent Garden", "Piccadilly Circus"
])
inject_duration = st.sidebar.slider("Simulation Duration (s)", 15, 60, 30)

if st.sidebar.button("🚨 Inject Crisis Event", use_container_width=True):
    success = trigger_injection(inject_cat, inject_landmark, inject_duration)
    if success:
        st.sidebar.success(f"Successfully injected active {inject_cat} crisis at {inject_landmark}!")
        st.balloons()
    else:
        st.sidebar.error("Failed to inject crisis event.")

st.sidebar.divider()

# Quick Presets
st.sidebar.markdown("#### Test Presets")
if st.sidebar.button("🔥 Fire at London Eye (30s)", use_container_width=True):
    if trigger_injection("Fire", "London Eye", 30):
        st.sidebar.success("Injected: Fire at London Eye")
        st.balloons()
        
if st.sidebar.button("🌊 Flooding near Big Ben (40s)", use_container_width=True):
    if trigger_injection("Flood", "Big Ben", 40):
        st.sidebar.success("Injected: Flood near Big Ben")
        st.balloons()
        
if st.sidebar.button("📣 Protests in Trafalgar Square (30s)", use_container_width=True):
    if trigger_injection("Civic Unrest", "Trafalgar Square", 30):
        st.sidebar.success("Injected: Protests in Trafalgar Square")
        st.balloons()
