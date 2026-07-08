# backend/app/telegram_notifier.py
"""
Telegram bot notifications for critical crisis alerts.
"""

import logging
import httpx
from backend.app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

CATEGORY_EMOJI = {
    "Fire":           "🔥",
    "Flood":          "🌊",
    "Earthquake":     "🌍",
    "Tsunami":        "🌊",
    "Tornado":        "🌪️",
    "Volcanic":       "🌋",
    "Landslide":      "⛰️",
    "Drought":        "☀️",
    "Civic Unrest":   "📣",
    "Outbreak":       "🦠",
    "Conflict":       "⚔️",
    "Infrastructure": "🏗️",
}


async def send_telegram_alert(alert: dict, llm_summary: str = ""):
    """Sends a Telegram message for a critical crisis alert."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not set. Skipping notification.")
        return

    category = alert.get("category", "Unknown")
    landmark = alert.get("landmark", "Unknown Location")
    z_score  = alert.get("z_score", 0.0)
    count    = alert.get("tweet_count", 0)
    alert_id = alert.get("id", "N/A")
    emoji    = CATEGORY_EMOJI.get(category, "🚨")

    message = (
        f"{emoji} *AEGISSTREAM CRISIS ALERT*\n\n"
        f"*Alert ID:* `{alert_id}`\n"
        f"*Category:* {category}\n"
        f"*Location:* {landmark}\n"
        f"*Clustered Reports:* {count}\n"
        f"*Anomaly Z-Score:* {z_score:.2f}σ\n"
    )

    if llm_summary:
        message += f"\n*🤖 AI Briefing:*\n_{llm_summary}_"

    message += "\n\n_Powered by AegisStream Real-Time Crisis Intelligence_"

    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                logger.info(f"Telegram alert sent for {alert_id}")
            else:
                logger.error(f"Telegram returned {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")