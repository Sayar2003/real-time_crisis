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
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import pydeck as pdk



st.set_page_config(
    page_title="AegisStream Dashboard",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://127.0.0.1:8000"

# ── Helper ──────────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color, alpha=0.08):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r},{g},{b},{alpha})'

CAT_COLORS = {
    "General":        "#6b7280",
    "Fire":           "#ff4757",
    "Flood":          "#1e90ff",
    "Earthquake":     "#f97316",
    "Tsunami":        "#06b6d4",
    "Tornado":        "#8b5cf6",
    "Volcanic":       "#ef4444",
    "Landslide":      "#92400e",
    "Drought":        "#d97706",
    "Civic Unrest":   "#ffa502",
    "Outbreak":       "#a855f7",
    "Conflict":       "#dc2626",
    "Infrastructure": "#64748b",
}

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

.stApp { background-color: #080c10; color: #c8d4e0; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 1rem !important; }

/* Top accent bar */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #66fcf1, #45f3ff, transparent);
    z-index: 999;
    animation: scan 3s ease-in-out infinite;
}
@keyframes scan { 0%,100%{opacity:0.4} 50%{opacity:1} }

/* Title */
.dashboard-title {
    color: #66fcf1;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 1.9rem;
    margin-bottom: 2px;
    letter-spacing: -0.5px;
}
.dashboard-subtitle {
    color: #4a6a7a;
    font-size: 0.8rem;
    margin-top: 0;
    margin-bottom: 18px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* Metric boxes */
.metric-box {
    background: linear-gradient(135deg, #0d1520 0%, #111c28 100%);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
    border: 1px solid #1a2a3a;
    position: relative;
    overflow: hidden;
}
.metric-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #66fcf1, transparent);
    opacity: 0.4;
}
.metric-label {
    font-size: 0.65rem;
    color: #4a6a7a;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 1.4rem;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.metric-value-critical { color: #ff4757; }
.metric-value-warning  { color: #ffa502; }
.metric-value-ok       { color: #2ed573; }
.metric-value-info     { color: #66fcf1; }

/* Metric pulse animations */
@keyframes critical-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(255,71,87,0); border-color: #ff475750; }
    50%      { box-shadow: 0 0 20px 4px rgba(255,71,87,0.2); border-color: #ff4757; }
}
@keyframes warning-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(255,165,2,0); border-color: #1a2a3a; }
    50%      { box-shadow: 0 0 16px 3px rgba(255,165,2,0.15); border-color: #ffa502; }
}
.metric-box-critical { animation: critical-pulse 2s ease-in-out infinite; }
.metric-box-warning  { animation: warning-pulse 2.5s ease-in-out infinite; }

/* Feed container */
.feed-container { max-height: 580px; overflow-y: auto; padding-right: 4px; }
.feed-container::-webkit-scrollbar { width: 4px; }
.feed-container::-webkit-scrollbar-track { background: transparent; }
.feed-container::-webkit-scrollbar-thumb { background: #1e2d3d; border-radius: 4px; }

/* Tweet cards */
.tweet-card {
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: #0d1520;
    border: 1px solid #1a2a3a;
    border-left: 3px solid #1e3a4a;
    transition: border-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
}
.tweet-card:hover            { border-left-color: #66fcf1; transform: translateX(2px); }
.tweet-card-fire:hover       { border-left-color: #ff4757 !important; box-shadow: -3px 0 12px rgba(255,71,87,0.2); }
.tweet-card-flood:hover      { border-left-color: #1e90ff !important; box-shadow: -3px 0 12px rgba(30,144,255,0.2); }
.tweet-card-unrest:hover     { border-left-color: #ffa502 !important; box-shadow: -3px 0 12px rgba(255,165,2,0.2); }
.tweet-card-outbreak:hover   { border-left-color: #a855f7 !important; box-shadow: -3px 0 12px rgba(168,85,247,0.2); }

.tweet-header {
    display: flex; align-items: center; gap: 6px;
    margin-bottom: 5px; flex-wrap: wrap;
}
.category-badge {
    font-weight: 600; font-size: 0.65rem;
    padding: 2px 7px; border-radius: 4px; color: #ffffff;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em; flex-shrink: 0;
}
.badge-general  { background: #2d3748; color: #a0aec0; }
.badge-fire     { background: #2d1515; color: #fc8181; border: 1px solid #fc818150; }
.badge-earthquake    { background: #2d1a0e; color: #fb923c; border: 1px solid #fb923c50; }
.badge-tsunami       { background: #0a2030; color: #22d3ee; border: 1px solid #22d3ee50; }
.badge-tornado       { background: #1e1030; color: #a78bfa; border: 1px solid #a78bfa50; }
.badge-volcanic      { background: #2d0a0a; color: #f87171; border: 1px solid #f87171050; }
.badge-landslide     { background: #1a1008; color: #d97706; border: 1px solid #d9770650; }
.badge-drought       { background: #2d1f00; color: #fbbf24; border: 1px solid #fbbf2450; }
.badge-conflict      { background: #2d0505; color: #f87171; border: 1px solid #f8717150; }
.badge-infrastructure{ background: #0f1620; color: #94a3b8; border: 1px solid #94a3b850; }
.badge-flood    { background: #152040; color: #63b3ed; border: 1px solid #63b3ed50; }
.badge-unrest   { background: #2d2515; color: #f6e05e; border: 1px solid #f6e05e50; }
.badge-outbreak { background: #251535; color: #b794f4; border: 1px solid #b794f450; }
.landmark-tag { color: #66fcf1; font-size: 0.7rem; font-weight: 500; flex-shrink: 0; }
.tweet-time   { color: #2d4a5a; font-size: 0.65rem; font-family: 'JetBrains Mono', monospace; margin-left: auto; flex-shrink: 0; }
.tweet-text   { margin: 0; color: #8aa4b8; font-size: 0.78rem; line-height: 1.4; }

/* Section header */
.section-header {
    font-size: 0.7rem; color: #4a6a7a;
    text-transform: uppercase; letter-spacing: 0.12em;
    font-family: 'JetBrains Mono', monospace;
    padding-bottom: 6px; border-bottom: 1px solid #1a2a3a;
    margin-bottom: 12px; position: relative;
}
.section-header::after {
    content: ''; position: absolute;
    bottom: -1px; left: 0; width: 40px; height: 1px;
    background: #66fcf1; box-shadow: 0 0 8px rgba(102,252,241,0.5);
}

/* Live dot */
@keyframes live-pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.5; transform:scale(0.85); }
}
.live-dot {
    display: inline-block; width: 7px; height: 7px;
    background: #2ed573; border-radius: 50%;
    margin-right: 6px; vertical-align: middle;
    animation: live-pulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 6px rgba(46,213,115,0.5);
}

/* Buttons */
.stButton > button[kind="primary"] {
    background: #0a2010 !important; color: #2ed573 !important;
    border: 1px solid #2ed57350 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important; letter-spacing: 0.05em !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: #0d2a18 !important; border-color: #2ed573 !important;
    box-shadow: 0 0 16px rgba(46,213,115,0.3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button {
    background: #0d1520 !important; color: #8aa4b8 !important;
    border: 1px solid #1a2a3a !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important; letter-spacing: 0.03em !important;
    transition: all 0.2s ease !important; border-radius: 6px !important;
}
.stButton > button:hover {
    color: #66fcf1 !important; border-color: #66fcf150 !important;
    box-shadow: 0 0 12px rgba(102,252,241,0.15) !important;
    transform: translateY(-1px) !important;
}

/* Streamlit overrides */
.stAlert { border-radius: 8px !important; }
div[data-testid="stInfo"] { background: #0d1a24 !important; border-color: #1a3a4a !important; }
h3 { color: #c8d4e0 !important; font-size: 0.9rem !important; font-weight: 500 !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    .dashboard-title {
        color: #66fcf1;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.6rem;
        margin-bottom: 2px;
        letter-spacing: -0.5px;
        padding-top: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


# ── Data fetching ─────────────────────────────────────────────────────────────
def fetch_tweets():
    try:
        r = requests.get(f"{BACKEND_URL}/api/tweets?limit=30", timeout=5.0)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return []

def fetch_alerts():
    try:
        r = requests.get(f"{BACKEND_URL}/api/alerts", timeout=5.0)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return {"active": [], "resolved": []}

def fetch_status():
    try:
        r = requests.get(f"{BACKEND_URL}/api/status", timeout=5.0)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return None


# ── Load state ────────────────────────────────────────────────────────────────
status_data = fetch_status()
tweets_data = fetch_tweets()
alerts_data = fetch_alerts()

# ── Offline screen ────────────────────────────────────────────────────────────
if status_data is None:
    st.markdown("<h1 class='dashboard-title'>🚨 AegisStream</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#ff4757;'>Backend API Server is Offline</h4>", unsafe_allow_html=True)
    st.info("""
    **Start the backend pipeline:**
```powershell
    python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
    """)
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("<div class='dashboard-title'>🛡️ AegisStream</div>", unsafe_allow_html=True)
st.markdown("<div class='dashboard-subtitle'>Real-Time Crisis Intelligence · Spatio-Temporal Anomaly Detection</div>", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────────────────────
active_alerts   = alerts_data.get("active", []) if isinstance(alerts_data, dict) else []
active_cnt      = len(active_alerts)
throughput      = status_data.get("throughput_tps", 0.0)
total_processed = status_data.get("total_tweets_processed", 0)
accuracy        = status_data.get("classifier_accuracy", 0.0)

if active_cnt >= 3:
    status_label, status_class, pulse_class = "CRITICAL", "metric-value-critical", "metric-box-critical"
elif active_cnt >= 1:
    status_label, status_class, pulse_class = "ACTIVE WARNINGS", "metric-value-warning", "metric-box-warning"
else:
    status_label, status_class, pulse_class = "MONITORING", "metric-value-ok", ""

acc_class = "metric-value-ok" if accuracy >= 70 else "metric-value-warning" if accuracy >= 50 else "metric-value-critical"

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
with m_col1:
    st.markdown(f"<div class='metric-box {pulse_class}'><div class='metric-label'>Alert Level</div><div class='metric-value {status_class}'>{status_label}</div></div>", unsafe_allow_html=True)
with m_col2:
    st.markdown(f"<div class='metric-box'><div class='metric-label'>Active Clusters</div><div class='metric-value metric-value-info'>{active_cnt}</div></div>", unsafe_allow_html=True)
with m_col3:
    st.markdown(f"<div class='metric-box'><div class='metric-label'>Throughput</div><div class='metric-value metric-value-info'>{throughput:.1f}<span style='font-size:0.75rem;color:#4a6a7a;'> posts/s</span></div></div>", unsafe_allow_html=True)
with m_col4:
    st.markdown(f"<div class='metric-box'><div class='metric-label'>Processed</div><div class='metric-value metric-value-info'>{total_processed:,}</div></div>", unsafe_allow_html=True)
with m_col5:
    st.markdown(f"<div class='metric-box'><div class='metric-label'>Accuracy</div><div class='metric-value {acc_class}'>{accuracy:.1f}%</div></div>", unsafe_allow_html=True)

st.write("")

# ── Main layout ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([0.65, 0.35])

with col_left:
    tab1, tab2 = st.tabs(["🗺️ Crisis Map", "🌪️ Live Weather"])
    with tab1:
        st.markdown("<div class='section-header'>🗺️ Spatio-Temporal Event Epicenters</div>", unsafe_allow_html=True)

        tweets_list, alerts_list = [], []

        for t in tweets_data:
            if isinstance(t, dict) and t.get("lat") is not None and t.get("lon") is not None:
                cat = t.get("category", "General")
                color_map = {
                    "Fire":           [231, 76,  60,  200],
                    "Flood":          [52,  152, 219, 200],
                    "Earthquake":     [249, 115, 22,  200],
                    "Tsunami":        [6,   182, 212, 200],
                    "Tornado":        [139, 92,  246, 200],
                    "Volcanic":       [239, 68,  68,  200],
                    "Landslide":      [146, 64,  14,  200],
                    "Drought":        [217, 119, 6,   200],
                    "Civic Unrest":   [241, 196, 15,  200],
                    "Outbreak":       [168, 85,  247, 200],
                    "Conflict":       [220, 38,  38,  200],
                    "Infrastructure": [100, 116, 139, 200],
                }
                tweets_list.append({
                    "lat": t["lat"], "lon": t["lon"], "category": cat,
                    "landmark": t.get("landmark", "Unknown"),
                    "color": color_map.get(cat, [46,204,113,100]),
                    "tweet_count": 1, "z_score": "N/A"
                })

        for a in active_alerts:
            if isinstance(a, dict) and a.get("lat") is not None and a.get("lon") is not None:
                alerts_list.append({
                    "lat": a["lat"], "lon": a["lon"],
                    "category": a.get("category", "Alert"),
                    "tweet_count": a.get("tweet_count", 0),
                    "z_score": round(a.get("z_score", 0.0), 2),
                    "landmark": a.get("landmark", "Detected Cluster")
                })

        df_tweets = pd.DataFrame(tweets_list) if tweets_list else pd.DataFrame(
            columns=["lat","lon","category","landmark","color","tweet_count","z_score"])
        df_alerts = pd.DataFrame(alerts_list) if alerts_list else pd.DataFrame(
            columns=["lat","lon","category","tweet_count","z_score","landmark"])

        # ── Map centroid ──
        map_focus = st.session_state.get("map_focus")

        
        if alerts_list:
            center_lat = np.mean([a["lat"] for a in alerts_list])
            center_lon = np.mean([a["lon"] for a in alerts_list])
            zoom = 3.0
        else:
            center_lat, center_lon, zoom = 20.0, 10.0, 1.8

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            initial_view_state=pdk.ViewState(
                latitude=center_lat,
                longitude=center_lon,
                zoom=zoom,
                pitch=20
            ),
            layers=[
                pdk.Layer("HeatmapLayer", data=df_tweets, get_position="[lon, lat]",
                        get_weight=1, radiusPixels=60, opacity=0.4),
                pdk.Layer("ScatterplotLayer", data=df_tweets, get_position="[lon, lat]",
                        get_color="color", get_radius=120, pickable=True),
                pdk.Layer("ScatterplotLayer", data=df_alerts, get_position="[lon, lat]",
                        get_color="[231,76,60,60]", get_line_color="[231,76,60,255]",
                        line_width_min_pixels=2, get_radius=600, pickable=True),
            ],
            tooltip={
                "html": "<b>Category:</b> {category}<br/><b>Landmark:</b> {landmark}<br/><b>Reports:</b> {tweet_count}<br/><b>Z-Score:</b> {z_score}",
                "style": {"background-color":"#0d1520","color":"#ffffff","border":"1px solid #66fcf1","border-radius":"6px","padding":"8px","font-family":"JetBrains Mono, monospace","font-size":"12px"}
            },
            height=480
        ), key=f"map_{center_lat:.4f}_{center_lon:.4f}_{zoom}")

        # ── Charts ────────────────────────────────────────────────────────────────
        st.write("")
        st.markdown("<div class='section-header'>📊 Real-Time Stream Analytics</div>", unsafe_allow_html=True)
        c_chart2 = st.container()

        base_layout = dict(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#6a8a9a', family='JetBrains Mono, monospace', size=11),
            xaxis=dict(gridcolor='#0d1a24', linecolor='#1a2a3a',
                    tickfont=dict(color='#4a6a7a', size=10),
                    showspikes=True, spikecolor='#66fcf1',
                    spikethickness=1, spikedash='dot'),
            yaxis=dict(gridcolor='#0d1a24', linecolor='#1a2a3a',
                    tickfont=dict(color='#4a6a7a', size=10),
                    showspikes=True, spikecolor='#66fcf1',
                    spikethickness=1, spikedash='dot'),
            legend=dict(bgcolor='rgba(8,12,16,0.8)', bordercolor='#1a2a3a',
                        borderwidth=1, font=dict(size=10, color='#8aa4b8'),
                        orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
            hoverlabel=dict(bgcolor='#0d1520', bordercolor='#66fcf1',
                            font=dict(color='#c8d4e0', size=11, family='JetBrains Mono, monospace')),
            hovermode='x unified',
            margin=dict(l=40, r=20, t=60, b=40),
            height=300,
        )

        title_style = dict(font=dict(size=13, color='#c8d4e0', family='Inter, sans-serif'), x=0.02, y=0.97)

        with c_chart2:
            if len(tweets_data) > 0:
                df_cat = pd.DataFrame(tweets_data)
                if 'category' in df_cat.columns:
                    counts = df_cat['category'].value_counts().reset_index()
                    counts.columns = ['Category', 'Volume']
                    counts = counts[counts['Volume'] > 0]

                    fig_bar = go.Figure()
                    fig_bar.add_trace(go.Bar(
                        x=counts['Category'], y=counts['Volume'],
                        marker=dict(color=[CAT_COLORS.get(c, '#4a6a7a') for c in counts['Category']],
                                    opacity=0.85, line=dict(width=0)),
                        hovertemplate='<b>%{x}</b><br>%{y} posts<extra></extra>',
                        text=counts['Volume'], textposition='outside',
                        textfont=dict(color='#6a8a9a', size=11, family='JetBrains Mono, monospace'),
                    ))
                    bar_layout = {**base_layout}
                    bar_layout['xaxis'] = {**base_layout['xaxis'], 'showspikes': False}
                    bar_layout['hovermode'] = 'x'
                    fig_bar.update_layout(**bar_layout, bargap=0.3,
                                        title=dict(text='Category Distribution', **title_style))
                    st.plotly_chart(fig_bar, use_container_width=True, theme=None)
            else:
                st.info("Waiting for stream data...")
        
        # --- EVENT TIMELINE ---
        st.write("")
        st.markdown("<div class='section-header'>📅 Crisis Event Timeline (Last 24 Hours)</div>", unsafe_allow_html=True)

        if len(tweets_data) > 0:
            df_timeline = pd.DataFrame(tweets_data)
            if 'timestamp' in df_timeline.columns:
                df_timeline['datetime'] = pd.to_datetime(df_timeline['timestamp'], unit='s')
                df_timeline['hour'] = df_timeline['datetime'].dt.floor('h')

                hourly = df_timeline.groupby(['hour','category']).size().reset_index(name='count')

                fig_timeline = go.Figure()
                for cat, color in CAT_COLORS.items():
                    cat_data = hourly[hourly['category'] == cat]
                    if len(cat_data) == 0:
                        continue
                    fig_timeline.add_trace(go.Bar(
                        x=cat_data['hour'],
                        y=cat_data['count'],
                        name=cat,
                        marker_color=color,
                        opacity=0.8,
                        hovertemplate=f'<b>{cat}</b><br>%{{y}} events<br>%{{x}}<extra></extra>',
                    ))

                fig_timeline.update_layout(
                    # FIX: STRIP BOTH CONFLICTING KEYS ('height' AND 'margin') DURING THE UNPACKING PROCESS
                    **{k: v for k, v in base_layout.items() if k not in ('height', 'margin')},
                    
                    title=dict(text='Hourly Crisis Event Distribution', **title_style),
                    barmode='stack',
                    height=220,  
                    margin=dict(l=40, r=20, t=40, b=40),  # THIS WILL NOW SAFELY SPECIFY ENGINE CUSTOM MARGINS
                    showlegend=False,
                )
                st.plotly_chart(fig_timeline, use_container_width=True, theme=None)

    with tab2:
        st.markdown("<div class='section-header'>Live Global Weather — Powered by Windy</div>", unsafe_allow_html=True)
        st.components.v1.iframe(
            "https://embed.windy.com/embed2.html?lat=20&lon=10&detailLat=20&detailLon=10&width=650&height=450&zoom=2&level=surface&overlay=wind&product=ecmwf&menu=&message=true&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=default&metricTemp=default&radarRange=-1",
            height=480,
            scrolling=False
        )
        st.caption("🌪️ Live wind patterns, storm tracks, and precipitation — updated every 3 hours from ECMWF model")
        
with col_right:
    st.markdown("<div class='section-header'>🔔 Active Alerts Inbox</div>", unsafe_allow_html=True)
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
            a_time     = time.strftime('%H:%M:%S', time.localtime(a.get('start_time', time.time())))
            llm_summary = a.get("llm_summary", "")

            # Countdown timer
            elapsed = time.time() - a.get('start_time', time.time())
            timeout = 300
            remaining = max(0, int(timeout - elapsed))

            mins_left = remaining // 60
            secs_left = remaining % 60

            countdown_str = (
                f"{mins_left}m {secs_left}s"
                if mins_left > 0
                else f"{secs_left}s"
            )

            countdown_color = (
                "#ff4757" if remaining < 60
                else "#ffa502" if remaining < 120
                else "#2ed573"
            ) 

            st.error(f"""
            🔴 **{a_cat} ALERT — {a_id}**
            * **Epicenter:** {a_landmark}
            * **Coordinates:** {a_lat:.4f}, {a_lon:.4f}
            * **Volume:** {a_vol} clustered reports
            * **Z-Score:** {a_z:.2f}σ
            * **Since:** {a_time}
            """)

            st.markdown(f"""
            <div style='display:flex;justify-content:space-between;align-items:center;
            background:#0a0c10;border:1px solid #1a2a3a;border-radius:6px;
            padding:6px 12px;margin-top:-8px;margin-bottom:8px;'>
            <span style='font-size:0.65rem;color:#4a6a7a;
            font-family:JetBrains Mono,monospace;
            text-transform:uppercase;letter-spacing:0.08em;'>
            Auto-resolves in
            </span>

            <span style='font-size:0.85rem;color:{countdown_color};
            font-family:JetBrains Mono,monospace;
            font-weight:600;'>
            {countdown_str}
            </span>
            </div>
            """, unsafe_allow_html=True)

            if llm_summary:
                st.markdown(f"""
                <div style='background:#0a1020;border-left:3px solid #66fcf1;
                padding:10px 14px;border-radius:0 6px 6px 0;
                font-size:12px;color:#8aa4b8;margin-bottom:12px;
                font-family:Inter,sans-serif;line-height:1.5;'>
                <span style='color:#66fcf1;font-weight:600;font-size:11px;
                font-family:JetBrains Mono,monospace;letter-spacing:0.05em;'>
                🤖 AI BRIEFING
                </span><br/><br/>
                {llm_summary}
                </div>
                """, unsafe_allow_html=True)

    st.write("")
    st.markdown("<div class='section-header'><span class='live-dot'></span>Live Signal Feed</div>", unsafe_allow_html=True)

    feed_html = "<div class='feed-container'>"
    if len(tweets_data) == 0:
        feed_html += "<p style='color:#4a6a7a;font-size:0.8rem;font-family:JetBrains Mono,monospace;'>Waiting for stream ingestion...</p>"
    else:
        card_cat_classes = {
            "Fire": "tweet-card-fire", "Flood": "tweet-card-flood",
            "Civic Unrest": "tweet-card-unrest", "Outbreak": "tweet-card-outbreak"
        }
        for t in tweets_data[:30]:
            if isinstance(t, dict):
                cat          = t.get("category", "General")
                badge_class = {
                    "Fire":           "badge-fire",
                    "Flood":          "badge-flood",
                    "Civic Unrest":   "badge-unrest",
                    "Outbreak":       "badge-outbreak",
                    "Earthquake":     "badge-earthquake",
                    "Tsunami":        "badge-tsunami",
                    "Tornado":        "badge-tornado",
                    "Volcanic":       "badge-volcanic",
                    "Landslide":      "badge-landslide",
                    "Drought":        "badge-drought",
                    "Conflict":       "badge-conflict",
                    "Infrastructure": "badge-infrastructure",
                }.get(cat, "badge-general")
                
                cat_class    = card_cat_classes.get(cat, "")
                landmark     = t.get("landmark", "Unknown")
                t_time       = time.strftime("%H:%M:%S", time.localtime(t.get("timestamp", time.time())))
                text         = t.get("text", "")
                
                # --- NEW EXTRACTS FOR SEVERITY & SOURCE LINKS ---
                severity_score = t.get("severity_score", 0)
                severity_label = t.get("severity_label", "")
                severity_color = t.get("severity_color", "#6b7280")
                source         = t.get("source", "simulator")
                source_url     = t.get("source_url", "")

                # SOURCE BADGE MATCHING MAP
                if source == "gdelt":
                    source_badge = "🌐"
                    source_color_hex = "#66fcf1"
                elif source == "openweathermap":
                    source_badge = "🌤️"
                    source_color_hex = "#3b82f6"
                elif source == "newsapi":
                    source_badge = "📰"
                    source_color_hex = "#a855f7"
                else:
                    source_badge = "🤖 SIM"
                    source_color_hex = "#2d4a5a"

                # CARD CONTAINER AND HEADER RENDER
                card  = f"<div class='tweet-card {cat_class}'>"
                card += "<div class='tweet-header'>"
                card += f"<span class='category-badge {badge_class}'>{cat.upper()}</span>"
                card += f"<span class='landmark-tag'>📍 {landmark}</span>"
                card += f"<span style='font-size:0.65rem;color:{source_color_hex};font-family:JetBrains Mono,monospace;'>{source_badge}</span>"
                card += f"<span class='tweet-time'>{t_time}</span>"
                card += "</div>"

                # INJECT SEVERITY BADGE SUB-CONTAINER IF PRESENT
                if severity_label:
                    card += f"<div style='margin-bottom:5px;'><span style='font-size:0.6rem;font-family:JetBrains Mono,monospace;color:{severity_color};background:{severity_color}20;padding:1px 6px;border-radius:3px;border:1px solid {severity_color}40;'>{severity_label} {severity_score}/10</span></div>"

                # TEXT BODY CONTAINER
                card += f"<p class='tweet-text'>{text}</p>"

                # INJECT REDIRECT HYPERLINK TO SOURCES
                if source_url and source_url != "nan":
                    card += f"<a href='{source_url}' target='_blank' style='font-size:0.65rem;color:#4a6a7a;text-decoration:none;font-family:JetBrains Mono,monospace;'>↗ Source</a>"

                card += "</div>"
                feed_html += card

    feed_html += "</div>"
    st.markdown(feed_html, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown("""
<div style='padding:4px 0 16px 0;'>
    <div style='font-size:1.1rem;font-weight:600;color:#66fcf1;font-family:Inter,sans-serif;letter-spacing:-0.3px;'>🛡️ AegisStream</div>
    <div style='font-size:0.65rem;color:#4a6a7a;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;'>Global Crisis Intelligence</div>
</div>
""", unsafe_allow_html=True)

if status_data:
    uptime       = status_data.get('uptime_seconds', 0)
    mins, secs   = divmod(uptime, 60)
    uptime_str   = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    
    # EXTRACT ALL INDIVIDUAL STREAM COUNT STATISTICS FROM THE INCOMING DETECTOR STATUS
    gdelt_count  = status_data.get('gdelt_events', 0)
    weather_count = status_data.get('weather_events', 0)
    news_count   = status_data.get('news_events', 0)

    st.sidebar.markdown(f"""
    <div style='background:#0d1520;border:1px solid #1a2a3a;border-radius:8px;padding:12px 14px;margin-bottom:12px;'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
            <span style='font-size:0.65rem;color:#4a6a7a;text-transform:uppercase;letter-spacing:0.08em;font-family:JetBrains Mono,monospace;'>System Status</span>
            <span style='font-size:0.65rem;color:#2ed573;font-family:JetBrains Mono,monospace;background:#0a2010;padding:1px 8px;border-radius:4px;border:1px solid #2ed57330;'>● LIVE</span>
        </div>
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
            <div style='background:#080c10;border-radius:6px;padding:8px 10px;border:1px solid #1a2a3a;'>
                <div style='font-size:0.6rem;color:#4a6a7a;text-transform:uppercase;margin-bottom:3px;'>Uptime</div>
                <div style='font-size:0.9rem;color:#c8d4e0;font-family:JetBrains Mono,monospace;font-weight:500;'>{uptime_str}</div>
            </div>
            <div style='background:#080c10;border-radius:6px;padding:8px 10px;border:1px solid #1a2a3a;'>
                <div style='font-size:0.6rem;color:#4a6a7a;text-transform:uppercase;margin-bottom:3px;'>Total Events</div>
                <div style='font-size:0.9rem;color:#c8d4e0;font-family:JetBrains Mono,monospace;font-weight:500;'>{status_data.get('total_tweets_processed', 0):,}</div>
            </div>
            <div style='background:#080c10;border-radius:6px;padding:8px 10px;border:1px solid #1a2a3a;'>
                <div style='font-size:0.6rem;color:#66fcf1;text-transform:uppercase;margin-bottom:3px;'>🌐 GDELT</div>
                <div style='font-size:0.9rem;color:#66fcf1;font-family:JetBrains Mono,monospace;font-weight:500;'>{gdelt_count}</div>
            </div>
            <div style='background:#080c10;border-radius:6px;padding:8px 10px;border:1px solid #1a2a3a;'>
                <div style='font-size:0.6rem;color:#3b82f6;text-transform:uppercase;margin-bottom:3px;'>🌤️ Weather</div>
                <div style='font-size:0.9rem;color:#3b82f6;font-family:JetBrains Mono,monospace;font-weight:500;'>{weather_count}</div>
            </div>
            <div style='background:#080c10;border-radius:6px;padding:8px 10px;border:1px solid #1a2a3a;grid-column: span 2;'>
                <div style='font-size:0.6rem;color:#a855f7;text-transform:uppercase;margin-bottom:3px;'>📰 NewsAPI</div>
                <div style='font-size:0.9rem;color:#a855f7;font-family:JetBrains Mono,monospace;font-weight:500;'>{news_count}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("""
<div style='background:#0d1520;border:1px solid #1a2a3a;border-radius:8px;padding:10px 14px;margin-bottom:12px;'>
    <div style='font-size:0.65rem;color:#4a6a7a;text-transform:uppercase;letter-spacing:0.1em;font-family:JetBrains Mono,monospace;margin-bottom:10px;'>Detection Parameters</div>
    <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2a3a;'>
        <span style='font-size:0.72rem;color:#6a8a9a;'>DBSCAN Epsilon</span>
        <span style='font-size:0.72rem;color:#66fcf1;font-family:JetBrains Mono,monospace;'>0.01 (~1.1km)</span>
    </div>
    <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2a3a;'>
        <span style='font-size:0.72rem;color:#6a8a9a;'>Min Cluster Size</span>
        <span style='font-size:0.72rem;color:#66fcf1;font-family:JetBrains Mono,monospace;'>4 events</span>
    </div>
    <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2a3a;'>
        <span style='font-size:0.72rem;color:#6a8a9a;'>Temporal Window</span>
        <span style='font-size:0.72rem;color:#66fcf1;font-family:JetBrains Mono,monospace;'>3.0 min</span>
    </div>
    <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2a3a;'>
        <span style='font-size:0.72rem;color:#6a8a9a;'>Z-Score Threshold</span>
        <span style='font-size:0.72rem;color:#66fcf1;font-family:JetBrains Mono,monospace;'>3.0σ</span>
    </div>
    <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2a3a;'>
        <span style='font-size:0.72rem;color:#6a8a9a;'>GDELT Poll Rate</span>
        <span style='font-size:0.72rem;color:#66fcf1;font-family:JetBrains Mono,monospace;'>15 min</span>
    </div>
    <div style='display:flex;justify-content:space-between;padding:5px 0;'>
        <span style='font-size:0.72rem;color:#6a8a9a;'>Crisis Categories</span>
        <span style='font-size:0.72rem;color:#66fcf1;font-family:JetBrains Mono,monospace;'>12 types</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style='background:#0d1520;border:1px solid #1a2a3a;border-radius:8px;padding:10px 14px;'>
    <div style='font-size:0.65rem;color:#4a6a7a;text-transform:uppercase;letter-spacing:0.1em;font-family:JetBrains Mono,monospace;margin-bottom:10px;'>Crisis Categories</div>
    <div style='display:flex;flex-wrap:wrap;gap:5px;'>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#2d1515;color:#fc8181;'>🔥 Fire</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#152040;color:#63b3ed;'>🌊 Flood</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#2d1a0e;color:#fb923c;'>🌍 Earthquake</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#0a2030;color:#22d3ee;'>🌊 Tsunami</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#1e1030;color:#a78bfa;'>🌪️ Tornado</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#2d0a0a;color:#f87171;'>🌋 Volcanic</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#1a1008;color:#d97706;'>⛰️ Landslide</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#2d1f00;color:#fbbf24;'>☀️ Drought</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#2d2515;color:#f6e05e;'>📣 Unrest</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#251535;color:#b794f4;'>🦠 Outbreak</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#2d0505;color:#f87171;'>⚔️ Conflict</span>
        <span style='font-size:0.65rem;padding:2px 8px;border-radius:10px;background:#0f1620;color:#94a3b8;'>🏗️ Infrastructure</span>
    </div>
</div>
""", unsafe_allow_html=True)