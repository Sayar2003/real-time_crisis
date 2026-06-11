# backend/app/processor.py

import re
import math
import asyncio
import logging
from typing import Dict, List, Tuple, Optional
from backend.app.config import LANDMARKS, CATEGORIES, CRISIS_CATEGORIES, CITY_ANCHOR

logger = logging.getLogger(__name__)

# Try to load spaCy, fall back gracefully if model not downloaded yet
nlp = None
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy 'en_core_web_sm' model not found. Will download and load later. Falling back to keyword geocoding.")
except ImportError:
    logger.warning("spaCy package not installed. Falling back to keyword geocoding.")

def clean_text(text: str) -> str:
    """Cleans raw text by removing links, special characters, and extra spaces."""
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)  # #FloodAlert → FloodAlert (keep the word)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def geocode_tweet(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extracts landmark names from text and maps them to coordinates.
    Matches landmarks directly using keywords, and falls back to spaCy NER.
    Returns (lat, lon, resolved_landmark_name) or (None, None, None).
    """
    text_lower = text.lower()
    
    # 1. Direct Keyword Matching (Primary & extremely accurate for configuration landmarks)
    for landmark, coords in LANDMARKS.items():
        landmark_words = set(landmark.lower().split())
        text_words = set(re.findall(r"\w+", text_lower))
        # Must share at least one full word — prevents "eye" matching "london eye"
        if landmark_words & text_words:
            return coords[0], coords[1], landmark.title()

    # 2. spaCy Named Entity Recognition fallback
    global nlp
    if nlp is not None:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC", "FAC"]:
                    ent_text = ent.text.lower().strip()
                    # Look for fuzzy/partial matches in configuration landmarks
                    for landmark, coords in LANDMARKS.items():
                        if landmark in ent_text or ent_text in landmark:
                            return coords[0], coords[1], landmark.title()
        except Exception as e:
            logger.error(f"Error during spaCy NER: {e}")
            
    return None, None, None

# Maximum distance in degrees to assign a landmark (~5.5 km)
MAX_LANDMARK_DISTANCE = 0.05

def get_nearest_landmark(lat: float, lon: float) -> str:
    """
    Returns the name of the closest landmark to the given coordinates.
    Returns 'Unknown Location' if no landmark is within MAX_LANDMARK_DISTANCE.
    """
    min_dist = float('inf')
    closest = "Unknown Location"

    for landmark, coords in LANDMARKS.items():
        dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            closest = landmark.title()

    # Only return the landmark if it's within the threshold distance
    if min_dist <= MAX_LANDMARK_DISTANCE:
        return closest

    return "Unknown Location"

class CrisisClassifier:
    """
    Zero-shot crisis classifier using facebook/bart-large-mnli.
    No training data needed — works on any real-world text immediately.
    Falls back to keyword matching if the model fails to load.
    """

    LABEL_MAP = {
        "fire or explosion emergency":          "Fire",
        "flood or storm disaster":              "Flood",
        "civil unrest or protest violence":     "Civic Unrest",
        "disease outbreak or health emergency": "Outbreak",
        "general social media post":            "General"
    }

    CANDIDATE_LABELS = list(LABEL_MAP.keys())

    KEYWORD_MAP = {
        "Fire":         ["fire", "blaze", "explosion", "smoke", "flames", "burning", "evacuate"],
        "Flood":        ["flood", "flooding", "submerged", "underwater", "storm", "overflow", "rain"],
        "Civic Unrest": ["protest", "riot", "demonstration", "clash", "unrest", "police", "march"],
        "Outbreak":     ["outbreak", "virus", "epidemic", "infection", "quarantine", "sick", "disease"],
    }

    def __init__(self):
        self.pipeline = None
        self._load_model()

    def _load_model(self):
        """Loads the zero-shot classification model. Falls back gracefully if unavailable."""
        try:
            logger.info("Loading zero-shot classifier (facebook/bart-large-mnli)...")
            from transformers import pipeline as hf_pipeline
            self.pipeline = hf_pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1   # CPU; change to 0 if you have a GPU
            )
            logger.info("Zero-shot classifier loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}. Using keyword fallback.")
            self.pipeline = None

    def predict(self, text: str) -> str:
        """
        Predicts crisis category for a given text.
        Uses zero-shot BART if available, falls back to keyword matching.
        """
        if not text or not text.strip():
            return "General"

        # --- Transformer path ---
        if self.pipeline is not None:
            try:
                result = self.pipeline(
                    text[:512],
                    self.CANDIDATE_LABELS,
                    multi_label=False
                )
                top_label = result["labels"][0]
                top_score = result["scores"][0]

                if top_score >= 0.4:
                    return self.LABEL_MAP.get(top_label, "General")
                return "General"

            except Exception as e:
                logger.error(f"Transformer inference failed: {e}. Using keyword fallback.")

        # --- Keyword fallback path ---
        return self._keyword_predict(text)

    def _keyword_predict(self, text: str) -> str:
        """Simple keyword voting classifier as fallback."""
        text_lower = text.lower()
        scores = {cat: 0 for cat in self.KEYWORD_MAP}

        for cat, keywords in self.KEYWORD_MAP.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[cat] += 1

        best_cat = max(scores, key=scores.get)
        if scores[best_cat] > 0:
            return best_cat
        return "General"

# Global instance of classifier
classifier = None

def get_classifier() -> CrisisClassifier:
    global classifier
    if classifier is None:
        classifier = CrisisClassifier()
    return classifier

async def get_classifier_async() -> CrisisClassifier:
    """Loads classifier in thread executor to avoid blocking the event loop."""
    global classifier
    if classifier is None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, get_classifier)
    return classifier

def reload_spacy():
    """Reloads spaCy if the model was downloaded after import."""
    global nlp
    if nlp is None:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully.")
        except Exception:
            pass
