"""
Service FinBERT — Analyse de sentiment financier (version mocké pour exécution locale).
"""
import logging

log = logging.getLogger(__name__)


class FinBERTError(Exception):
    pass


def analyze_sentiment(text: str) -> dict:
    """
    Analyse le sentiment du texte via heuristique de mots-clés.
    (FinBERT désactivé pour éviter la dépendance à torch/transformers)
    """
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.5}

    text_lower = text.lower()

    positive_words = ["growth", "profit", "surge", "gain", "up", "bull", "beat", "rise", "record", "strong", "positive"]
    negative_words = ["loss", "drop", "plunge", "down", "bear", "miss", "crash", "bankrupt", "decline", "weak", "risk"]

    pos_score = sum(1 for w in positive_words if w in text_lower)
    neg_score = sum(1 for w in negative_words if w in text_lower)

    if pos_score > neg_score:
        return {"label": "positive", "score": 0.8}
    elif neg_score > pos_score:
        return {"label": "negative", "score": 0.8}
    else:
        return {"label": "neutral", "score": 0.5}


def batch_analyze_sentiment(texts: list) -> list:
    """Analyse une liste de textes."""
    return [analyze_sentiment(t) for t in texts]


def sentiment_to_score(sentiment: dict) -> float:
    """
    Convertit un résultat de sentiment en score numérique [-1, 1].
    positive = +score, negative = -score, neutral = 0
    """
    label = sentiment.get("label", "neutral")
    score = sentiment.get("score", 0.5)

    if label == "positive":
        return score
    elif label == "negative":
        return -score
    else:
        return 0.0
