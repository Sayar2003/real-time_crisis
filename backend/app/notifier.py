# backend/app/notifier.py

import logging
import httpx
from backend.app.config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


async def send_slack_alert(alert: dict, llm_summary: str = ""):
    """
    Sends a formatted Slack notification when a critical alert fires.
    Uses httpx async client — non-blocking.
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook URL not set. Skipping notification.")
        return

    category  = alert.get("category", "Unknown")
    landmark  = alert.get("landmark", "Unknown Location")
    z_score   = alert.get("z_score", 0.0)
    count     = alert.get("tweet_count", 0)
    alert_id  = alert.get("id", "N/A")
    lat       = alert.get("lat", 0.0)
    lon       = alert.get("lon", 0.0)

    # Category emoji map
    emoji_map = {
        "Fire":         "🔥",
        "Flood":        "🌊",
        "Civic Unrest": "📣",
        "Outbreak":     "🦠",
    }
    emoji = emoji_map.get(category, "🚨")

    # Build Slack Block Kit message — rich formatted card
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} AEGISSTREAM CRISIS ALERT — {category.upper()}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Alert ID:*\n{alert_id}"},
                    {"type": "mrkdwn", "text": f"*Category:*\n{category}"},
                    {"type": "mrkdwn", "text": f"*Epicenter:*\n{landmark}"},
                    {"type": "mrkdwn", "text": f"*Coordinates:*\n{lat:.4f}, {lon:.4f}"},
                    {"type": "mrkdwn", "text": f"*Clustered Reports:*\n{count} posts"},
                    {"type": "mrkdwn", "text": f"*Anomaly Z-Score:*\n{z_score:.2f}σ"},
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🤖 AI Situation Briefing:*\n{llm_summary if llm_summary else '_Generating briefing..._'}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚡ Powered by AegisStream Real-Time Crisis Intelligence"
                    }
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=5.0
            )
            if response.status_code == 200:
                logger.info(f"Slack notification sent for {alert_id} ({category} at {landmark})")
            else:
                logger.error(f"Slack webhook returned {response.status_code}: {response.text}")

    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")