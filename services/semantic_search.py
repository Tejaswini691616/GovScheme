# PATH: GovScheme/services/semantic_search.py
"""Local, dependency-light multilingual scheme search.

It combines Unicode character TF-IDF similarity, domain-language glossary
normalization and citizen-profile boosts. It never invents scheme facts.
"""
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models.scheme_model import get_all_schemes
from ai.language_service import translate_keywords_to_english

DOMAIN_EXPANSIONS = {
    "farmer": "farmer agriculture farming kisan crop खेती किसान कृषक",
    "student": "student education scholarship विद्यार्थी छात्र शिक्षा छात्रवृत्ति",
    "health": "health medical insurance healthcare स्वास्थ्य आरोग्य உடல்நலம் ఆరోగ్యం",
    "housing": "housing home house rural housing आवास வீடு ఇల్లు",
    "senior": "senior citizen pension old age वृद्ध ज्येष्ठ ಹಿರಿಯ",
    "disability": "disability disabled assistance दिव्यांग अपंग",
    "widow": "widow women महिला विधवा",
    "loan": "loan credit business mudra ऋण कर्ज कर्ज़",
    "pension": "pension retirement वृद्धावस्था पेंशन",
}


def _doc(s):
    return " ".join(str(s.get(k) or "") for k in ("scheme_name", "category", "description", "benefits", "eligibility", "documents_required", "state"))


def _normalize_query(query, language):
    glossary = translate_keywords_to_english(query, language)
    tokens = [query]
    if glossary:
        tokens.append(glossary)
        for token in glossary.split():
            tokens.append(DOMAIN_EXPANSIONS.get(token, token))
    return " ".join(tokens)


def semantic_search(query, language="English", user_id=None, limit=10):
    schemes = get_all_schemes()
    if not schemes:
        return []
    query = (query or "").strip()
    if not query:
        return [dict(s, search_score=0.0) for s in schemes[:limit]]
    docs = [_doc(s) for s in schemes]
    corpus = docs + [_normalize_query(query, language)]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
    matrix = vectorizer.fit_transform(corpus)
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()

    profile = None
    if user_id:
        from models.user_model import get_user_by_id
        profile = get_user_by_id(user_id)
    local = _normalize_query(query, language).lower()
    ranked = []
    for scheme, score in zip(schemes, scores):
        bonus = 0.0
        category = str(scheme.get("category") or "").lower()
        if any(k in local for k in ("farmer", "agriculture", "kisan")) and "agri" in category:
            bonus += 0.18
        if any(k in local for k in ("student", "education", "scholarship")) and any(x in category for x in ("education", "scholar")):
            bonus += 0.18
        if profile:
            if str(profile.get("farmer")) .lower() == "yes" and scheme.get("farmer_required"):
                bonus += 0.08
            if str(profile.get("student")) .lower() == "yes" and scheme.get("student_required"):
                bonus += 0.08
            if str(profile.get("senior_citizen")) .lower() == "yes" and scheme.get("max_age") is not None:
                bonus += 0.04
        ranked.append((min(1.0, float(score) + bonus), scheme))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [dict(s, search_score=round(sc * 100, 1)) for sc, s in ranked[:limit]]
