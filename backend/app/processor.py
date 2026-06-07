# backend/app/processor.py

import re
import math
import logging
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
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
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE) # remove URLs
    text = re.sub(r"@\w+", "", text) # remove mentions
    text = re.sub(r"\s+", " ", text).strip() # normalize whitespace
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
        if landmark in text_lower:
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

def get_nearest_landmark(lat: float, lon: float) -> str:
    """Returns the name of the closest landmark to the given coordinates."""
    min_dist = float('inf')
    closest = "London"
    for landmark, coords in LANDMARKS.items():
        # Using Euclidean distance as coordinates are localized in London
        dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            closest = landmark.title()
    return closest

class CrisisClassifier:
    """A lightweight text classifier trained on synthetic crisis text at startup."""
    def __init__(self):
        self.pipeline = None
        self.train_classifier()

    def train_classifier(self):
        """Generates synthetic dataset and fits TF-IDF + Naive Bayes pipeline."""
        logger.info("Generating synthetic training dataset for classifier...")
        
        # Base templates for generating training sentences
        templates = {
            "General": [
                "Enjoying a lovely walk around {landmark}.",
                "Traffic is a bit slow near {landmark} this afternoon.",
                "Having a delicious coffee and a pastry close to {landmark}.",
                "Beautiful weather at {landmark} right now!",
                "Shopping near {landmark}, it is incredibly crowded.",
                "Strolling through {landmark} on this nice day.",
                "Just passed by {landmark} on my commute back home.",
                "Met some old friends near {landmark} for a quick lunch.",
                "A lovely, quiet and peaceful evening around {landmark}.",
                "Stunning view of {landmark} today.",
                "Visiting {landmark} with family, having a great time.",
                "Beautiful sunset over {landmark}.",
                "Walking around the city, took a detour to {landmark}.",
                "The lights on {landmark} look beautiful tonight.",
                "Enjoying the weekend walk near {landmark}."
            ],
            "Fire": [
                "OMG! Huge fire near {landmark}! Smoke is rising high!",
                "Firefighters are battling a massive blaze at a building near {landmark}!",
                "There is a serious building fire close to {landmark}. Avoid the area!",
                "Smelling strong smoke and seeing flames near {landmark}. Stay safe!",
                "Building on fire near {landmark}. Fire alarms ringing everywhere!",
                "Massive explosion and fire near {landmark}! Rescue teams on scene.",
                "A warehouse is burning down close to {landmark}. Heavy smoke!",
                "Avoid the streets near {landmark}, fire trucks blocking road.",
                "Huge structure fire near {landmark}. Hope everyone got out safely.",
                "Emergency! Fire outbreak at a commercial building near {landmark}!"
            ],
            "Flood": [
                "Serious flooding near {landmark}! Roads are completely underwater!",
                "The water is rising fast around {landmark} after the heavy storm!",
                "Flooded streets close to {landmark}. Cars are submerged and stuck!",
                "Basements getting flooded near {landmark}. The rain won't stop.",
                "River overflowing near {landmark}. Flood warning issued!",
                "Severe flood alert near {landmark}. Avoid walking near the river.",
                "Flash flood drowning the roads near {landmark}. Stay indoors!",
                "Water levels reaching knee height near {landmark} after downpour.",
                "Emergency teams evacuating residents near {landmark} due to rising flood.",
                "Streets look like rivers near {landmark} due to heavy rain!"
            ],
            "Civic Unrest": [
                "Huge protest blocking the streets near {landmark}!",
                "Police and protestors clashing close to {landmark} right now.",
                "Massive demonstration near {landmark}, riot police are deployed!",
                "Avoid the area around {landmark}, the crowd is getting aggressive!",
                "Protestors chanting and blocking traffic near {landmark}.",
                "Violent clashes reported near {landmark}. Stay away from downtown.",
                "Rally turning violent near {landmark}. Police firing tear gas.",
                "Demonstration causing traffic chaos around {landmark}.",
                "Crowd blocking entrance to {landmark} during political protest.",
                "Civic unrest and riots breaking out near {landmark}."
            ],
            "Outbreak": [
                "Public health alert: several food poisoning cases reported near {landmark}!",
                "A sudden viral outbreak reported at a school near {landmark}.",
                "Dozens hospitalized with infection symptoms close to {landmark}.",
                "Warning: measles outbreak detected in the community around {landmark}.",
                "Many people falling sick near {landmark}. Local clinic is full.",
                "New bacterial infection outbreak detected near {landmark}.",
                "Health warning issued for the area around {landmark} due to virus outbreak.",
                "Salmonella outbreak linked to restaurants near {landmark}.",
                "Contagious flu spreading rapidly near {landmark}.",
                "Doctors report a spike in infectious cases near {landmark}."
            ]
        }
        
        X = []
        y = []
        
        # Populate training data by combining templates and landmarks
        for category, sentence_list in templates.items():
            for template in sentence_list:
                for landmark in LANDMARKS.keys():
                    # Generate variations
                    X.append(template.format(landmark=landmark.title()))
                    y.append(category)
                    
                    # Add noise variations (exclamation, hashtags)
                    X.append(template.format(landmark=landmark.title()) + " #Urgent")
                    y.append(category)
                    X.append(template.format(landmark=landmark.title()).lower())
                    y.append(category)
        
        # Build vectorization and classifier pipeline
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), stop_words="english")),
            ("clf", MultinomialNB(alpha=0.1))
        ])
        
        self.pipeline.fit(X, y)
        logger.info(f"Classifier trained successfully on {len(X)} samples.")

    def predict(self, text: str) -> str:
        """Predicts the category of a given text."""
        if self.pipeline is None:
            return "General"
        cleaned = clean_text(text)
        return self.pipeline.predict([cleaned])[0]

# Global instance of classifier
classifier = None

def get_classifier() -> CrisisClassifier:
    global classifier
    if classifier is None:
        classifier = CrisisClassifier()
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
