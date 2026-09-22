# PATH: GovScheme/ai/predict.py
"""
Loads the model trained by ai/train_model.py and scores citizen-scheme
pairs at inference time. The Flask app calls this module; it never
retrains a model on a request (see project spec, section 20/62).
"""
import os
import threading

import joblib
import pandas as pd

from config import Config

_lock = threading.Lock()
_model_cache = {"pipeline": None, "model_name": None}


def _load_model():
    with _lock:
        if _model_cache["pipeline"] is None and _model_cache.get("load_failed") is not True:
            if not os.path.exists(Config.ML_MODEL_PATH):
                _model_cache["load_failed"] = True
                return None
            try:
                bundle = joblib.load(Config.ML_MODEL_PATH)
                _model_cache["pipeline"] = bundle["pipeline"]
                _model_cache["model_name"] = bundle.get("model_name", "Unknown")
                _model_cache["load_failed"] = False
            except Exception as exc:
                # Persisted sklearn pipelines can be incompatible across major
                # sklearn versions. Never let that break the citizen dashboard.
                _model_cache["load_failed"] = True
                _model_cache["load_error"] = str(exc)
        return _model_cache["pipeline"]


def model_available() -> bool:
    return _load_model() is not None


def model_status() -> dict:
    pipeline = _load_model()
    return {
        "available": pipeline is not None,
        "model_name": _model_cache.get("model_name"),
        "fallback_active": pipeline is None,
        "load_error": _model_cache.get("load_error"),
    }


def _fallback_score(user_row: dict, scheme_row: dict) -> float:
    """Deterministic safety-net ranking used only when the persisted ML model
    cannot be loaded. It rewards how many configured scheme criteria the
    already-eligible citizen satisfies, so a broken model never produces
    identical/meaningless recommendations. The UI must label this as fallback
    relevance rather than ML probability."""
    checks = 0
    matches = 0
    pairs = [
        ("farmer_required", "farmer"), ("bpl_required", "bpl"),
        ("disability_required", "disabled"), ("student_required", "student"),
        ("widow_required", "widow"),
    ]
    for scheme_key, user_key in pairs:
        if scheme_row.get(scheme_key):
            checks += 1
            if str(user_row.get(user_key, "")).strip().lower() in {"yes","true","1","y"}:
                matches += 1
    if scheme_row.get("income_limit") is not None and user_row.get("annual_income") is not None:
        checks += 1
        if float(user_row["annual_income"]) <= float(scheme_row["income_limit"]): matches += 1
    if scheme_row.get("min_age") is not None and user_row.get("age") is not None:
        checks += 1
        if float(user_row["age"]) >= float(scheme_row["min_age"]): matches += 1
    if scheme_row.get("max_age") is not None and user_row.get("age") is not None:
        checks += 1
        if float(user_row["age"]) <= float(scheme_row["max_age"]): matches += 1
    return matches / checks if checks else 0.5


def _row_for_model(user_row: dict, scheme_row: dict) -> dict:
    """Builds a single-row feature dict matching ai/train_model.py's
    NUMERIC_FEATURES / CATEGORICAL_FEATURES column names."""
    return {
        "Age": user_row.get("age"),
        "Family_Size": user_row.get("family_size"),
        "Dependents": user_row.get("dependents"),
        "Annual_Family_Income": user_row.get("annual_income"),
        "Land_Holding_Acres": user_row.get("land_holding_acres"),
        "Disability_Percentage": user_row.get("disability_percentage"),
        "Gender": user_row.get("gender"),
        "State": user_row.get("state"),
        "Rural_Urban": user_row.get("rural_urban"),
        "Education": user_row.get("education"),
        "Occupation": user_row.get("occupation"),
        "Employment_Status": user_row.get("employment_status"),
        "Caste": user_row.get("caste"),
        "Minority": user_row.get("minority"),
        "Farmer": user_row.get("farmer"),
        "BPL": user_row.get("bpl"),
        "Disability": user_row.get("disabled"),
        "Student": user_row.get("student"),
        "Senior_Citizen": user_row.get("senior_citizen"),
        "Widow": user_row.get("widow"),
        "Min_Age": scheme_row.get("min_age"),
        "Max_Age": scheme_row.get("max_age"),
        "Income_Limit": scheme_row.get("income_limit"),
        "Category": scheme_row.get("category"),
        "Caste_Requirement": scheme_row.get("caste_requirement"),
        "Farmer_Required": "Yes" if scheme_row.get("farmer_required") else "No",
        "BPL_Required": "Yes" if scheme_row.get("bpl_required") else "No",
        "Disability_Required": "Yes" if scheme_row.get("disability_required") else "No",
        "Student_Required": "Yes" if scheme_row.get("student_required") else "No",
        "Widow_Required": "Yes" if scheme_row.get("widow_required") else "No",
    }


def score_schemes(user_row: dict, scheme_rows: list) -> list:
    """
    Returns list of (scheme_row, relevance_score) sorted descending.
    If no trained model exists yet, falls back to a neutral score of 0.5
    for every scheme so the app doesn't crash before ai/train_model.py
    has been run.
    """
    pipeline = _load_model()
    if not scheme_rows:
        return []
    if pipeline is None:
        scored = [(s, _fallback_score(user_row, s)) for s in scheme_rows]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    rows = [_row_for_model(user_row, s) for s in scheme_rows]
    X = pd.DataFrame(rows)
    proba = pipeline.predict_proba(X)[:, 1]
    scored = list(zip(scheme_rows, [float(p) for p in proba]))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
