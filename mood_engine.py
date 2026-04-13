"""
mood_engine.py — Semantic mood prediction for the journal.
"""

import re
import math
from collections import Counter


MOODS = {
    "Joyful":     {"emoji": "😄",  "color": "#E8A87C", "valence":  1.0, "arousal":  0.8},
    "Excited":    {"emoji": "🤩",  "color": "#D4A5C9", "valence":  0.9, "arousal":  1.0},
    "Calm":       {"emoji": "😌",  "color": "#8BAF8B", "valence":  0.6, "arousal": -0.3},
    "Grateful":   {"emoji": "🥰",  "color": "#C9808A", "valence":  0.8, "arousal":  0.2},
    "Hopeful":    {"emoji": "🙂",  "color": "#7BAF9E", "valence":  0.7, "arousal":  0.4},
    "Neutral":    {"emoji": "😐",  "color": "#A89BAE", "valence":  0.0, "arousal":  0.0},
    "Tired":      {"emoji": "😴",  "color": "#B8977A", "valence": -0.2, "arousal": -0.8},
    "Lonely":     {"emoji": "🥺",  "color": "#8C9EBF", "valence": -0.5, "arousal": -0.3},
    "Anxious":    {"emoji": "😰",  "color": "#9BB0C1", "valence": -0.4, "arousal":  0.8},
    "Sad":        {"emoji": "😢",  "color": "#7A90A8", "valence": -0.7, "arousal": -0.5},
    "Frustrated": {"emoji": "😖",  "color": "#C28B6B", "valence": -0.6, "arousal":  0.6},
    "Angry":      {"emoji": "😤",  "color": "#C07070", "valence": -0.8, "arousal":  0.9},
}

LEXICON = {
    "Joyful": [
        "happy", "happiness", "joy", "joyful", "wonderful", "amazing", "fantastic",
        "great", "awesome", "delighted", "ecstatic", "thrilled", "laugh", "laughed",
        "smile", "smiled", "smiling", "fun", "lovely", "beautiful", "perfect",
        "blessed", "love", "loved", "celebrate", "celebrated", "party", "best day",
        "incredible", "magnificent", "brilliant", "elated", "cheerful", "bright",
    ],
    "Excited": [
        "excited", "exciting", "can't wait", "cannot wait", "pumped", "stoked",
        "anticipating", "looking forward", "wow", "unbelievable", "thrilled",
        "hyped", "energized", "fired up", "adventure", "new opportunity",
        "big news", "surprise", "surprised", "amazing news", "can't believe",
    ],
    "Calm": [
        "calm", "peaceful", "relaxed", "serene", "tranquil", "quiet", "still",
        "content", "comfortable", "easy", "gentle", "soft", "slow", "rest",
        "rested", "meditation", "meditated", "breathe", "breathed", "mindful",
        "present", "grounded", "stable", "balanced", "at ease", "cozy",
        "soothed", "settled", "stillness", "unhurried",
    ],
    "Grateful": [
        "grateful", "gratitude", "thankful", "thank", "appreciate", "appreciated",
        "appreciation", "blessed", "fortunate", "lucky", "privilege", "privileged",
        "honor", "honored", "gift", "kind", "kindness", "generous",
        "generosity", "support", "supported", "helped", "caring", "cared for",
    ],
    "Hopeful": [
        "hopeful", "hope", "optimistic", "optimism", "looking up", "better days",
        "things will get better", "believe", "believing", "trust", "faith",
        "possibility", "potential", "chance", "new beginning", "fresh start",
        "turning point", "progress", "improving", "getting better", "forward",
    ],
    "Neutral": [
        "okay", "ok", "fine", "alright", "normal", "usual", "regular", "average",
        "nothing special", "just another", "routine", "ordinary", "standard",
        "typical", "so-so", "meh", "not bad", "not great",
    ],
    "Tired": [
        "tired", "exhausted", "exhaustion", "fatigue", "fatigued", "sleepy",
        "sleep deprived", "drained", "worn out", "burned out", "burnout",
        "no energy", "low energy", "sluggish", "heavy", "lethargic", "drowsy",
        "can't focus", "brain fog", "yawning", "need sleep", "depleted",
    ],
    "Lonely": [
        "lonely", "loneliness", "alone", "isolated", "isolation", "no one",
        "nobody", "by myself", "wish someone", "miss people", "disconnected",
        "left out", "excluded", "forgotten", "invisible", "unseen",
        "no friends", "misunderstood", "distant",
    ],
    "Anxious": [
        "anxious", "anxiety", "worried", "worry", "nervous", "stress", "stressed",
        "panic", "panicking", "overwhelmed", "scared", "fear", "afraid", "dread",
        "dreading", "overthinking", "racing thoughts", "uneasy", "tense",
        "on edge", "restless", "unsettled", "what if", "spiral", "spiraling",
    ],
    "Sad": [
        "sad", "sadness", "unhappy", "depressed", "depression", "cry", "cried",
        "crying", "tears", "heartbroken", "heartbreak", "miss", "missed",
        "missing", "loss", "lost", "grief", "grieving", "hopeless",
        "empty", "hollow", "numb", "pain", "hurt", "hurting", "dark",
        "down", "low", "blue", "gloomy", "melancholy",
    ],
    "Frustrated": [
        "frustrated", "frustration", "annoyed", "annoying", "irritated",
        "stuck", "blocked", "doesn't work", "not working", "again",
        "why", "ugh", "nothing works", "failed", "failure", "mistake",
        "messed up", "screwed up", "gave up", "wasted", "pointless",
    ],
    "Angry": [
        "angry", "anger", "furious", "rage", "mad", "livid", "infuriated",
        "outraged", "hate", "hated", "hateful", "disgusted", "can't stand",
        "fed up", "enough", "sick of", "explosive", "blew up",
        "yelled", "screamed", "unfair", "injustice",
    ],
}

INTENSIFIERS = {
    "very": 1.5, "really": 1.4, "so": 1.3, "extremely": 1.8, "incredibly": 1.7,
    "absolutely": 1.6, "totally": 1.4, "completely": 1.5, "utterly": 1.6,
    "insanely": 1.7, "super": 1.3, "quite": 1.2, "pretty": 1.1,"slightly":1.1,"kinda":1.1,"kind of":1.1
}
NEGATIONS = {
    "not", "no", "never", "don't", "doesn't", "didn't", "won't", "can't",
    "cannot", "neither", "nor", "hardly", "barely",
}


def _tokenize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return text.split()


def _get_ngrams(tokens, n):
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def _count_keywords(text, mood):
    tokens = _tokenize(text)
    keywords = LEXICON[mood]
    score = 0.0
    negation_window = 0
    bigrams = _get_ngrams(tokens, 2)
    trigrams = _get_ngrams(tokens, 3)
    all_phrases = set(tokens + bigrams + trigrams)

    for i, token in enumerate(tokens):
        if token in NEGATIONS:
            negation_window = 3
        if negation_window > 0:
            negation_window -= 1
        multiplier = 1.0
        if i > 0 and tokens[i - 1] in INTENSIFIERS:
            multiplier = INTENSIFIERS[tokens[i - 1]]
        for kw in keywords:
            if kw in all_phrases or token == kw:
                hit = multiplier * (0.5 if negation_window > 0 else 1.0)
                score += hit
                break
    return score


def predict_mood(text):
    if not text or not text.strip():
        return _empty_result()

    raw_scores = {mood: _count_keywords(text, mood) for mood in MOODS}
    total = sum(raw_scores.values())
    if total == 0:
        raw_scores["Neutral"] = 1.0

    exp_scores = {m: math.exp(s * 2) for m, s in raw_scores.items()}
    exp_total = sum(exp_scores.values())
    probs = {m: v / exp_total for m, v in exp_scores.items()}

    top_moods = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    primary_mood = top_moods[0][0]
    confidence = top_moods[0][1]

    valence = sum(probs[m] * MOODS[m]["valence"] for m in MOODS)
    arousal = sum(probs[m] * MOODS[m]["arousal"] for m in MOODS)

    if valence > 0.35:
        sentiment_label = "Positive"
    elif valence < -0.25:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Gentle"

    return {
        "primary_mood": primary_mood,
        "confidence": confidence,
        "scores": probs,
        "raw_scores": raw_scores,
        "valence": valence,
        "arousal": arousal,
        "top_moods": top_moods[:5],
        "word_count": len(_tokenize(text)),
        "sentiment_label": sentiment_label,
        "emoji": MOODS[primary_mood]["emoji"],
        "color": MOODS[primary_mood]["color"],
    }


def _empty_result():
    return {
        "primary_mood": "Neutral",
        "confidence": 0.0,
        "scores": {m: 0.0 for m in MOODS},
        "raw_scores": {m: 0.0 for m in MOODS},
        "valence": 0.0, "arousal": 0.0,
        "top_moods": [("Neutral", 1.0)],
        "word_count": 0,
        "sentiment_label": "Gentle",
        "emoji": "🌙", "color": "#A89BAE",
    }


def get_all_moods():
    return list(MOODS.keys())
