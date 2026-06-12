# backend/app/llm.py
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# Fetch API Key directly from environment/config variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

async def generate_alert_summary(alert: dict) -> str:
    """
    Calls Groq API to generate a lightning-fast 3-sentence situation briefing for a crisis alert.
    Returns a plain text summary or a fallback string if the API call fails.
    """
    if client is None:
        logger.warning("Groq API key not set. Skipping LLM summary.")
        return _fallback_summary(alert)

    category  = alert.get("category", "Unknown")
    landmark  = alert.get("landmark", "Unknown Location")
    z_score   = alert.get("z_score", 0.0)
    count     = alert.get("tweet_count", 0)
    lat       = alert.get("lat", 0.0)
    lon       = alert.get("lon", 0.0)

    # Pull sample post texts from the cluster for context
    sample_texts = [
        t.get("text", "")
        for t in alert.get("tweets", [])[:5]
        if t.get("text")
    ]
    samples_str = "\n".join(f"- {t}" for t in sample_texts) if sample_texts else "No sample posts available."

    prompt = f"""You are a crisis intelligence analyst. Based on the following real-time social media data, write a concise 3-sentence situation briefing.

Crisis Data:
- Category: {category}
- Location: {landmark} (lat: {lat:.4f}, lon: {lon:.4f})
- Clustered reports: {count} posts
- Anomaly Z-score: {z_score:.2f} (higher = more unusual vs baseline)

Sample social media posts from the cluster:
{samples_str}

Write exactly 3 sentences:
1. What is happening and where.
2. How severe and how fast it is spreading.
3. Recommended immediate action.

Be direct, factual, and concise. Do not use bullet points or markdown bolding inside the sentences."""

    try:
        # Utilizing Llama 3 70B on Groq for high-quality intelligence reporting at ultra-low latency
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are an emergency management AI. Speak factually and concisely without preamble."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )
        
        summary = completion.choices[0].message.content.strip()
        logger.info(f"Groq LLM summary generated for alert at {landmark}")
        return summary
        
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return _fallback_summary(alert)

def _fallback_summary(alert: dict) -> str:
    """Returns a basic summary when Groq API is unavailable."""
    category = alert.get("category", "Unknown")
    landmark = alert.get("landmark", "Unknown Location")
    count    = alert.get("tweet_count", 0)
    z_score  = alert.get("z_score", 0.0)
    return (
        f"A {category.lower()} event has been detected near {landmark} "
        f"based on {count} clustered social media reports. "
        f"Signal anomaly score is {z_score:.1f} standard deviations above baseline — "
        f"monitor the situation closely."
    )