# backend/app/severity.py
"""
Crisis Severity Scoring Engine
Scores each GDELT event 1-10 based on:
- Category weight
- Number of mentions/sources
- Tone negativity
- Credibility
"""

from backend.app.config import SEVERITY_WEIGHTS


def calculate_severity_score(event: dict) -> dict:
    """
    Calculates a severity score (1-10) for a crisis event.
    Returns the event with severity_score and severity_label added.
    """
    category     = event.get("category", "General")
    num_mentions = event.get("num_mentions", 1)
    num_articles = event.get("num_articles", 1)
    avg_tone     = event.get("avg_tone", 0.0)
    credibility  = event.get("credibility", 0.5)

    # Base score from category weight (0-4 points)
    category_weight = SEVERITY_WEIGHTS.get(category, 0.5)
    base_score      = min(category_weight * 2, 4.0)

    # Mention score (0-3 points) — more mentions = more severe
    mention_score = min(num_mentions / 10.0, 3.0)

    # Tone score (0-2 points) — more negative = more severe
    tone_score = min(abs(min(avg_tone, 0)) / 5.0, 2.0)

    # Credibility score (0-1 point)
    cred_score = credibility * 1.0

    # Total score 0-10
    total = base_score + mention_score + tone_score + cred_score
    total = round(min(max(total, 1.0), 10.0), 1)

    # Severity label
    if total >= 8:
        label = "CRITICAL"
        color = "#ff4757"
    elif total >= 6:
        label = "HIGH"
        color = "#ffa502"
    elif total >= 4:
        label = "MEDIUM"
        color = "#ffd32a"
    else:
        label = "LOW"
        color = "#2ed573"

    return {
        **event,
        "severity_score": total,
        "severity_label": label,
        "severity_color": color,
    }