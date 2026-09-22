# PATH: GovScheme/ai/train_model.py
"""
Trains the ML recommendation-ranking model.

Responsibility (per project spec):
    "Among the relevant/potentially eligible schemes, which schemes should
    be ranked higher for this citizen?"

This is a SEPARATE, offline training step. The Flask app never trains a
model on request; it only loads the joblib file this script produces.

Data leakage prevention:
    Each citizen appears in 20 rows (one per scheme). A plain random
    row-level split would let rows from the same citizen appear in both
    train and test, leaking citizen-specific signal. We split by
    Citizen_ID instead (80% of citizens -> train, 20% -> test), so all
    of a citizen's 20 records stay on one side of the split.

Run:
    python ai/train_model.py
"""
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, confusion_matrix)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

RANDOM_STATE = 42

CITIZEN_NUMERIC = ["Age", "Family_Size", "Dependents", "Annual_Family_Income",
                    "Land_Holding_Acres", "Disability_Percentage"]
CITIZEN_CATEGORICAL = ["Gender", "State", "Rural_Urban", "Education", "Occupation",
                        "Employment_Status", "Caste", "Minority", "Farmer", "BPL",
                        "Disability", "Student", "Senior_Citizen", "Widow"]
SCHEME_NUMERIC = ["Min_Age", "Max_Age", "Income_Limit"]
SCHEME_CATEGORICAL = ["Category", "Caste_Requirement", "Farmer_Required",
                       "BPL_Required", "Disability_Required", "Student_Required",
                       "Widow_Required"]

NUMERIC_FEATURES = CITIZEN_NUMERIC + SCHEME_NUMERIC
CATEGORICAL_FEATURES = CITIZEN_CATEGORICAL + SCHEME_CATEGORICAL


def load_merged_dataset():
    xls = pd.ExcelFile(Config.EXCEL_SOURCE_PATH)
    cp = pd.read_excel(xls, "Citizen_Profile")
    sm = pd.read_excel(xls, "Scheme_Master")
    er = pd.read_excel(xls, "Eligibility_Records")

    df = er.merge(cp, on="Citizen_ID", how="left").merge(
        sm, on="Scheme_ID", how="left", suffixes=("", "_scheme"))
    df["label"] = (df["Eligibility_Status"] == "Eligible").astype(int)

    # normalize boolean-ish scheme flag columns to string Yes/No so the
    # OneHotEncoder treats them consistently with citizen Yes/No columns
    for col in ["Farmer_Required", "BPL_Required", "Disability_Required",
                "Student_Required", "Widow_Required"]:
        df[col] = df[col].map(lambda v: "Yes" if bool(v) else "No")

    return df


def split_by_citizen(df, test_fraction=0.2):
    citizen_ids = np.array(df["Citizen_ID"].unique(), dtype=object)
    rng = np.random.RandomState(RANDOM_STATE)
    rng.shuffle(citizen_ids)
    n_test = int(len(citizen_ids) * test_fraction)
    test_ids = set(citizen_ids[:n_test])
    train_ids = set(citizen_ids[n_test:])

    train_df = df[df["Citizen_ID"].isin(train_ids)].reset_index(drop=True)
    test_df = df[df["Citizen_ID"].isin(test_ids)].reset_index(drop=True)
    return train_df, test_df, len(train_ids), len(test_ids)


def build_pipeline(classifier):
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric_transformer, NUMERIC_FEATURES),
        ("cat", categorical_transformer, CATEGORICAL_FEATURES),
    ])
    return Pipeline([
        ("preprocess", preprocessor),
        ("classifier", classifier),
    ])


def precision_recall_at_k(df_test, y_pred_proba, k=5):
    """Ranking metric: for each citizen, take top-K predicted schemes and
    measure precision/recall against actual 'Eligible' label."""
    work = df_test.copy()
    work["pred_proba"] = y_pred_proba
    precisions, recalls = [], []
    for cid, group in work.groupby("Citizen_ID"):
        group = group.sort_values("pred_proba", ascending=False)
        top_k = group.head(k)
        actual_eligible = group["label"].sum()
        hits = top_k["label"].sum()
        precisions.append(hits / k)
        if actual_eligible > 0:
            recalls.append(hits / actual_eligible)
    return float(np.mean(precisions)), float(np.mean(recalls)) if recalls else 0.0


def main():
    print("Loading merged dataset from Excel...")
    df = load_merged_dataset()

    train_df, test_df, n_train_citizens, n_test_citizens = split_by_citizen(df)
    print(f"Citizens -> train: {n_train_citizens}, test: {n_test_citizens}")
    print(f"Records  -> train: {len(train_df)}, test: {len(test_df)}")

    X_train, y_train = train_df, train_df["label"]
    X_test, y_test = test_df, test_df["label"]

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=12, random_state=RANDOM_STATE),
    }

    results = {}
    best_name, best_pipeline, best_f1 = None, None, -1

    for name, clf in candidates.items():
        print(f"\nTraining {name}...")
        pipe = build_pipeline(clf)
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        y_proba = pipe.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()
        p_at_5, r_at_5 = precision_recall_at_k(X_test, y_proba, k=5)

        results[name] = {
            "accuracy": acc, "precision": prec, "recall": rec, "f1_score": f1,
            "confusion_matrix": cm, "precision_at_5": p_at_5, "recall_at_5": r_at_5,
        }
        print(f"  Accuracy={acc:.4f} Precision={prec:.4f} Recall={rec:.4f} F1={f1:.4f} "
              f"P@5={p_at_5:.4f} R@5={r_at_5:.4f}")

        if f1 > best_f1:
            best_f1, best_name, best_pipeline = f1, name, pipe

    print(f"\nBest model by F1-score: {best_name} (F1={best_f1:.4f})")

    os.makedirs(os.path.dirname(Config.ML_MODEL_PATH), exist_ok=True)
    joblib.dump({"pipeline": best_pipeline, "model_name": best_name}, Config.ML_MODEL_PATH)
    print(f"Saved model to {Config.ML_MODEL_PATH}")

    metrics_out = {
        "results": results,
        "best_model": best_name,
        "train_citizens": n_train_citizens,
        "test_citizens": n_test_citizens,
        "train_records": len(train_df),
        "test_records": len(test_df),
    }
    with open(Config.ML_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, indent=2)
    print(f"Saved metrics to {Config.ML_METRICS_PATH}")


if __name__ == "__main__":
    main()
