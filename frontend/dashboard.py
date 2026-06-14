# frontend/dashboard.py
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from streamlit_autorefresh import st_autorefresh
import pydeck as pdk
import plotly.express as px

st.set_page_config(
    page_title="AegisStream Dashboard",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://127.0.0.1:8000"

st.markdown("""
<style>
    .stApp { background-color: #0b0c10; color: #e0e6ed; }
    .dashboard-title {
        color: #66fcf1; font-family: 'Outfit', sans-serif;
        font-weight: 800; font-size: 2.2rem; margin-bottom: 0px;
        text-shadow: 0 0 15px rgba(102, 252, 241, 0.5);
    }
    .dashboard-subtitle {
        color: #45f3ff; font-size: 0.95rem;
        margin-top: 0px; margin-bottom: 20px; opacity: 0.95;
    }
    .feed-container { max-height: 550px; overflow-y: auto; padding-right: 5px; }
    .tweet-card {
        border-radius: 8px; padding: 12px; margin-bottom: 10px;
        background-color: #1f2833; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease;
    }
    .tweet-card:hover { transform: translateY(-2px); }
    .tweet-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .category-badge {
        font-weight: bold; font-size: 0.75rem;
        padding: 2px 8px; border-radius: 4px; color: #ffffff;
    }
    .badge-general { background-color: #7f8c8d; }
    .badge-fire { background-color: #e74c3c; box-shadow: 0 0 5px rgba(231,76,60,0.5); }
    .badge-flood { background-color: #3498db; box-shadow: 0 0 5px rgba(52,152,219,0.5); }
    .badge-unrest { background-color: #f1c40f; color: #000000; box-shadow: 0 0 5px rgba(241,196,15,0.5); }
    .badge-outbreak { background-color: #9b59b6; box-shadow: 0 0 5px rgba(155,89,182,0.5); }
    .landmark-tag { color: #66fcf1; font-size: 0.75rem; font-weight: 500; }
    .tweet-time { color: #b0b0c8; font-size: 0.72rem; }
    .tweet-text { margin: 0; color: #ffffff; font-size: 0.82rem; line-height: 1.35; }
    .metric-box {
        background-color: #1f2833; border-radius: 8px;
        padding: 15px; text-align: center; border: 1px solid #2d3748;
    }
    .metric-value-critical { color: #ff4d4d; font-size: 2rem; font-weight: bold; text-shadow: 0 0 12px rgba(255,77,77,0.4); }
    .metric-value-warning  { color: #ffd43b; font-size: 2rem; font-weight: bold; text-shadow: 0 0 12px rgba(255,212,59,0.4); }
    .metric-value-ok       { color: #2ecc71; font-size: 2rem; font-weight: bold; text-shadow: 0 0 12px rgba(46,204,113,0.4); }
    .metric-value-info     { color: #66fcf1; font-size: 2rem; font-weight: bold; text-shadow: 0 0 12px rgba(102,252,241,0.4); }
    .feed-container p  { color: #ffffff !important; }
    .feed-container li { color: #f7fafc !important; }
</style>
""", unsafe_allow_html=True)

st_refresh = st_autorefresh(interval=5000, key="data_refresh_trigger")


# --- DATA POLLING ---
def fetch_tweets():
    try:
        response = requests.get(f"{BACKEND_URL}/api/tweets?limit=30", timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

def fetch_alerts():
    try:
        response = requests.get(f"{BACKEND_URL}/api/alerts", timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"active": [], "resolved": []}

def fetch_status():
    try:
        response = requests.get(f"{BACKEND_URL}/api/status", timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def trigger_injection(category, landmark, duration=30):
    try:
        payload = {"category": category, "landmark": landmark, "duration": duration}
        response = requests.post(f"{BACKEND_URL}/api/inject", json=payload, timeout=2.0)
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
    python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
    """)
    st.stop()

# --- APP LAYOUT ---
st.markdown("<div class='dashboard-title'>🛡️ AegisStream Crisis Intelligence</div>", unsafe_allow_html=True)
st.markdown("<div class='dashboard-subtitle'>Real-Time Data Streaming & Spatial-Temporal Anomaly Detector</div>", unsafe_allow_html=True)

# --- METRICS ---
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

active_alerts = alerts_data.get("active", []) if isinstance(alerts_data, dict) else []
active_cnt    = len(active_alerts)
throughput    = status_data.get("throughput_tps", 0.0)
total_processed = status_data.get("total_tweets_processed", 0)

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
    st.markdown(f"<div class='metric-box'><div style='font-size:0.75rem;color:#b0b0c8;text-transform:uppercase;font-weight:600;'>System Alert Level</div><div class='{status_class}'>{status_label}</div></div>", unsafe_allow_html=True)
with m_col2:
    st.markdown(f"<div class='metric-box'><div style='font-size:0.75rem;color:#b0b0c8;text-transform:uppercase;font-weight:600;'>Active Event Clusters</div><div class='metric-value-info'>{active_cnt}</div></div>", unsafe_allow_html=True)
with m_col3:
    st.markdown(f"<div class='metric-box'><div style='font-size:0.75rem;color:#b0b0c8;text-transform:uppercase;font-weight:600;'>Pipeline Throughput</div><div class='metric-value-info'>{throughput:.1f} <span style='font-size:0.9rem;'>tweets/s</span></div></div>", unsafe_allow_html=True)
with m_col4:
    st.markdown(f"<div class='metric-box'><div style='font-size:0.75rem;color:#b0b0c8;text-transform:uppercase;font-weight:600;'>Total Streams Processed</div><div class='metric-value-info'>{total_processed}</div></div>", unsafe_allow_html=True)
with m_col5:
    accuracy = status_data.get("classifier_accuracy", 0.0)
    acc_class = "metric-value-ok" if accuracy >= 70 else "metric-value-warning" if accuracy >= 50 else "metric-value-critical"
    st.markdown(f"<div class='metric-box'><div style='font-size:0.75rem;color:#b0b0c8;text-transform:uppercase;font-weight:600;'>Classifier Accuracy</div><div class='{acc_class}'>{accuracy:.1f}%</div></div>", unsafe_allow_html=True)

st.write("")

col_left, col_right = st.columns([0.65, 0.35])

with col_left:
    st.markdown("### 🗺️ Spatio-Temporal Event Epicenters")

    tweets_list = []
    for t in tweets_data:
        if isinstance(t, dict) and t.get("lat") is not None and t.get("lon") is not None:
            cat = t.get("category", "General")
            if cat == "Fire":         color = [231, 76, 60, 180]
            elif cat == "Flood":      color = [52, 152, 219, 180]
            elif cat == "Civic Unrest": color = [241, 196, 15, 180]
            elif cat == "Outbreak":   color = [155, 89, 182, 180]
            else:                     color = [46, 204, 113, 100]
            tweets_list.append({
                "lat": t["lat"], "lon": t["lon"],
                "category": cat,
                "landmark": t.get("landmark", "Unknown"),
                "color": color,
                "tweet_count": 1,
                "z_score": "N/A"
            })

    df_tweets = pd.DataFrame(tweets_list) if tweets_list else pd.DataFrame(
        columns=["lat", "lon", "category", "landmark", "color", "tweet_count", "z_score"])

    alerts_list = []
    for a in active_alerts:
        if isinstance(a, dict) and a.get("lat") is not None and a.get("lon") is not None:
            alerts_list.append({
                "lat": a["lat"], "lon": a["lon"],
                "category": a.get("category", "Alert"),
                "tweet_count": a.get("tweet_count", 0),
                "z_score": round(a.get("z_score", 0.0), 2),
                "landmark": a.get("landmark", "Detected Cluster")
            })
    df_alerts = pd.DataFrame(alerts_list) if alerts_list else pd.DataFrame(
        columns=["lat", "lon", "category", "tweet_count", "z_score", "landmark"])

    # Dynamic map centroid
    if alerts_list:
        center_lat = np.mean([a["lat"] for a in alerts_list])
        center_lon = np.mean([a["lon"] for a in alerts_list])
        zoom = 11.0
    elif tweets_list:
        center_lat = np.mean([t["lat"] for t in tweets_list])
        center_lon = np.mean([t["lon"] for t in tweets_list])
        zoom = 10.0
    else:
        center_lat, center_lon, zoom = 20.0, 0.0, 1.5

    view_state = pdk.ViewState(
        latitude=center_lat, longitude=center_lon,
        zoom=zoom, pitch=20
    )

    heatmap_layer = pdk.Layer(
        "HeatmapLayer", data=df_tweets,
        get_position="[lon, lat]",
        get_weight=1, radiusPixels=60, opacity=0.4,
    )
    tweets_layer = pdk.Layer(
        "ScatterplotLayer", data=df_tweets,
        get_position="[lon, lat]",
        get_color="color", get_radius=120, pickable=True
    )
    alerts_layer = pdk.Layer(
        "ScatterplotLayer", data=df_alerts,
        get_position="[lon, lat]",
        get_color="[231, 76, 60, 60]",
        get_line_color="[231, 76, 60, 255]",
        line_width_min_pixels=2, get_radius=600, pickable=True
    )

    tooltip = {
        "html": """
            <b>Category:</b> {category}<br/>
            <b>Landmark:</b> {landmark}<br/>
            <b>Reports:</b> {tweet_count}<br/>
            <b>Z-Score:</b> {z_score}
        """,
        "style": {
            "background-color": "#1f2833", "color": "#ffffff",
            "border": "1px solid #45f3ff",
            "border-radius": "6px", "padding": "8px"
        }
    }

    st.pydeck_chart(pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        initial_view_state=view_state,
        layers=[heatmap_layer, tweets_layer, alerts_layer],
        tooltip=tooltip, height=500
    ))

    # --- CHARTS ---
    st.markdown("### 📊 Real-Time Stream Analytics")
    c_chart1, c_chart2 = st.columns(2)

    plotly_layout_theme = dict(
        template="plotly_dark",
        paper_bgcolor='#1f2833', plot_bgcolor='#1a222d',
        font=dict(color='#ffffff', family='Outfit, sans-serif'),
        title=dict(font=dict(size=15, color='#66fcf1'), y=0.93, yref='container', x=0.05),
        xaxis=dict(gridcolor='#2d3748', linecolor='#45f3ff', tickfont=dict(color='#e0e6ed', size=11)),
        yaxis=dict(gridcolor='#2d3748', linecolor='#45f3ff', tickfont=dict(color='#e0e6ed', size=11))
    )

    with c_chart1:
        if len(tweets_data) > 0:
            df_chart = pd.DataFrame(tweets_data)
            if 'timestamp' in df_chart.columns and 'category' in df_chart.columns:
                df_chart['datetime'] = pd.to_datetime(df_chart['timestamp'], unit='s')
                df_chart['time_bin'] = df_chart['datetime'].dt.floor('10s')
                grouped = df_chart.groupby(['time_bin', 'category']).size().unstack(fill_value=0).reset_index()
                for c in ["General", "Fire", "Flood", "Civic Unrest", "Outbreak"]:
                    if c not in grouped.columns:
                        grouped[c] = 0
                melted = grouped.melt(
                    id_vars=['time_bin'],
                    value_vars=["General", "Fire", "Flood", "Civic Unrest", "Outbreak"],
                    var_name='Category', value_name='Volume'
                )
                fig_line = px.line(
                    melted, x='time_bin', y='Volume', color='Category',
                    color_discrete_map={"General": "#2ecc71", "Fire": "#e74c3c",
                                        "Flood": "#3498db", "Civic Unrest": "#f1c40f", "Outbreak": "#9b59b6"},
                    title="Historical Signal Trends (10s Bins)",
                    labels={"time_bin": "Timeline", "Volume": "Posts/s"}
                )
                fig_line.update_layout(
                    plotly_layout_theme,
                    margin=dict(l=40, r=20, t=85, b=40), height=360,
                    legend=dict(orientation="h", yanchor="top", y=0.88,
                                xanchor="left", x=0.05,
                                font=dict(size=10, color='#ffffff'),
                                bgcolor='rgba(0,0,0,0)')
                )
                st.plotly_chart(fig_line, use_container_width=True, theme=None)

    with c_chart2:
        if len(tweets_data) > 0:
            df_cat = pd.DataFrame(tweets_data)
            if 'category' in df_cat.columns:
                counts = df_cat['category'].value_counts().reset_index()
                counts.columns = ['Category', 'Volume']
                fig_bar = px.bar(
                    counts, x='Category', y='Volume', color='Category',
                    color_discrete_map={"General": "#2ecc71", "Fire": "#e74c3c",
                                        "Flood": "#3498db", "Civic Unrest": "#f1c40f", "Outbreak": "#9b59b6"},
                    title="Total Stream Volume by Category",
                    labels={"Category": "Crisis Sector", "Volume": "Total Messages"}
                )
                fig_bar.update_layout(
                    plotly_layout_theme,
                    margin=dict(l=40, r=20, t=85, b=40),
                    height=360, showlegend=False
                )
                st.plotly_chart(fig_bar, use_container_width=True, theme=None)

with col_right:
    st.markdown("### 🔔 Active Alerts Inbox")
    if not active_alerts:
        st.info("No active crisis events detected.")
    else:
        for a in active_alerts:
            a_id       = a.get('id', 'UNK')
            a_cat      = a.get('category', 'Unknown').upper()
            a_lat      = a.get('lat', 0.0)
            a_lon      = a.get('lon', 0.0)
            a_vol      = a.get('tweet_count', 0)
            a_z        = a.get('z_score', 0.0)
            a_landmark = a.get('landmark', 'Unknown Location')
            a_time_raw = a.get('start_time', time.time())
            a_time     = time.strftime('%H:%M:%S', time.localtime(a_time_raw))
            llm_summary = a.get("llm_summary", "")

            st.error(f"""
            🔴 **{a_cat} ALERT ({a_id})**
            * **Epicenter:** {a_landmark} (lat: {a_lat:.4f}, lon: {a_lon:.4f})
            * **Volume:** {a_vol} clustered reports
            * **Signal Z-score:** {a_z:.2f}
            * **Active since:** {a_time}
            """)

            if llm_summary:
                st.markdown(f"""
                <div style='background:#1a1a2e;border-left:3px solid #45f3ff;
                padding:10px 14px;border-radius:0 6px 6px 0;
                font-size:13px;color:#c8d4e0;margin-top:-10px;margin-bottom:15px;'>
                🤖 <b style='color:#45f3ff'>Groq AI Intelligence Briefing</b><br/>{llm_summary}
                </div>
                """, unsafe_allow_html=True)

    st.write("")
    st.markdown("### 💬 Live Social Media Stream")
    feed_html = "<div class='feed-container'>"

    if len(tweets_data) == 0:
        feed_html += "<p style='color:#b0b0c8;font-size:0.85rem;'>Waiting for social media stream ingestion...</p>"
    else:
        for t in tweets_data[:30]:
            if isinstance(t, dict):
                cat = t.get("category", "General")
                badge_class = "badge-general"
                if cat == "Fire":         badge_class = "badge-fire"
                elif cat == "Flood":      badge_class = "badge-flood"
                elif cat == "Civic Unrest": badge_class = "badge-unrest"
                elif cat == "Outbreak":   badge_class = "badge-outbreak"

                landmark     = t.get("landmark", "Unknown")
                t_time       = time.strftime("%H:%M:%S", time.localtime(t.get("timestamp", time.time())))
                text         = t.get("text", "")
                source       = t.get("source", "simulator")
                source_badge = "🌐 GDELT" if source == "gdelt" else "🤖 SIM"
                source_color = "#45f3ff" if source == "gdelt" else "#7a90a4"

                feed_html += f"""
                <div class='tweet-card'>
                    <div class='tweet-header'>
                        <span class='category-badge {badge_class}'>{cat.upper()}</span>
                        <span class='landmark-tag'>📍 {landmark}</span>
                        <span style='font-size:0.7rem;color:{source_color};'>{source_badge}</span>
                        <span class='tweet-time'>{t_time}</span>
                    </div>
                    <p class='tweet-text'>{text}</p>
                </div>
                """

    feed_html += "</div>"
    st.markdown(feed_html, unsafe_allow_html=True)


# --- SIDEBAR ---
st.sidebar.markdown("<h2 style='color:#66fcf1;'>⚙️ AegisStream Control Panel</h2>", unsafe_allow_html=True)
if status_data:
    st.sidebar.write(f"**Backend Status:** Operational (Uptime: {status_data.get('uptime_seconds', 0)}s)")
    st.sidebar.write(f"**Queue Depth:** {status_data.get('raw_queue_depth', 0)} raw posts")
    st.sidebar.write(f"**Classifier Accuracy:** {status_data.get('classifier_accuracy', 0.0):.1f}%")
    st.sidebar.write(f"**Correct Predictions:** {status_data.get('correct_predictions', 0)}/{status_data.get('total_predictable', 0)}")

st.sidebar.divider()
st.sidebar.markdown("#### Analytics Engine Parameters")
st.sidebar.markdown("- **DBSCAN Epsilon (Spatial):** `0.01` (~1.1 km)")
st.sidebar.markdown("- **DBSCAN Min Samples:** `4` tweets")
st.sidebar.markdown("- **ST-DBSCAN Temporal Window:** `3.0` minutes")
st.sidebar.markdown("- **Anomaly Z-score Threshold:** `3.0` standard deviations")

st.sidebar.divider()
st.sidebar.markdown("### 🚀 Manual Crisis Injector")
st.sidebar.write("Simulate a localized crisis signal event:")

inject_cat = st.sidebar.selectbox("Crisis Category", ["Fire", "Flood", "Civic Unrest", "Outbreak"])
inject_landmark = st.sidebar.selectbox("Epicenter Landmark", [
    "Big Ben", "Hyde Park", "London Eye", "Tower Bridge",
    "Trafalgar Square", "Soho", "Piccadilly Circus",
    "India Gate", "Connaught Place", "Red Fort", "Chandni Chowk",
    "Motijheel", "Gulshan", "Dhanmondi", "Old Dhaka",
    "Monas", "Kota Tua", "Sudirman", "Kemang",
])
inject_duration = st.sidebar.slider("Simulation Duration (s)", 15, 60, 30)

if st.sidebar.button("🚨 Inject Crisis Event", use_container_width=True):
    success = trigger_injection(inject_cat, inject_landmark, inject_duration)
    if success:
        st.sidebar.success(f"Injected {inject_cat} crisis at {inject_landmark}!")
    else:
        st.sidebar.error("Failed to inject crisis event.")

st.sidebar.divider()
st.sidebar.markdown("#### Test Presets")
if st.sidebar.button("🔥 Fire at London Eye (30s)", use_container_width=True):
    if trigger_injection("Fire", "London Eye", 30):
        st.sidebar.success("Injected: Fire at London Eye")

if st.sidebar.button("🌊 Flooding near Big Ben (40s)", use_container_width=True):
    if trigger_injection("Flood", "Big Ben", 40):
        st.sidebar.success("Injected: Flood near Big Ben")

if st.sidebar.button("📣 Protests in Trafalgar Square (30s)", use_container_width=True):
    if trigger_injection("Civic Unrest", "Trafalgar Square", 30):
        st.sidebar.success("Injected: Protests in Trafalgar Square")