# PATH: GovScheme/tools/model_experiments.py
"""Robustness experiments for the SmartGov AI recommendation model.

Runs multiple citizen-level dataset splits derived from the official project
workbook without changing the source workbook:
  1) 80/20 random citizen split (baseline)
  2) 70/30 random citizen split
  3) 90/10 random citizen split
  4) State-holdout split (hold out two states when possible)

Each experiment evaluates Logistic Regression, Decision Tree and Random Forest.
The production model is NOT replaced by this script. Results are written to
ml_models/experiments/results.json and results.csv.
"""
import json, os, sys
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

RANDOM_STATE = 42
CITIZEN_NUMERIC = ["Age", "Family_Size", "Dependents", "Annual_Family_Income", "Land_Holding_Acres", "Disability_Percentage"]
CITIZEN_CATEGORICAL = ["Gender", "State", "Rural_Urban", "Education", "Occupation", "Employment_Status", "Caste", "Minority", "Farmer", "BPL", "Disability", "Student", "Senior_Citizen", "Widow"]
SCHEME_NUMERIC = ["Min_Age", "Max_Age", "Income_Limit"]
SCHEME_CATEGORICAL = ["Category", "Caste_Requirement", "Farmer_Required", "BPL_Required", "Disability_Required", "Student_Required", "Widow_Required"]
NUMERIC_FEATURES = CITIZEN_NUMERIC + SCHEME_NUMERIC
CATEGORICAL_FEATURES = CITIZEN_CATEGORICAL + SCHEME_CATEGORICAL


def load_data():
    xls = pd.ExcelFile(Config.EXCEL_SOURCE_PATH)
    cp = pd.read_excel(xls, "Citizen_Profile")
    sm = pd.read_excel(xls, "Scheme_Master")
    er = pd.read_excel(xls, "Eligibility_Records")
    df = er.merge(cp, on="Citizen_ID", how="left").merge(sm, on="Scheme_ID", how="left")
    df["label"] = (df["Eligibility_Status"].astype(str).str.strip().str.lower() == "eligible").astype(int)
    for col in ["Farmer_Required", "BPL_Required", "Disability_Required", "Student_Required", "Widow_Required"]:
        df[col] = df[col].map(lambda v: "Yes" if bool(v) else "No")
    return df


def pipeline(name):
    num = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    cat = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    prep = ColumnTransformer([("num", num, NUMERIC_FEATURES), ("cat", cat, CATEGORICAL_FEATURES)])
    clf = {
        "LogisticRegression": LogisticRegression(max_iter=1200, random_state=RANDOM_STATE),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(n_estimators=60, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1),
    }[name]
    return Pipeline([("preprocess", prep), ("classifier", clf)])


def ranking_metrics(test_df, proba, k=5):
    w = test_df[["Citizen_ID", "label"]].copy(); w["score"] = proba
    ps=[]; rs=[]
    for _, g in w.groupby("Citizen_ID"):
        top = g.sort_values("score", ascending=False).head(k)
        actual = int(g["label"].sum()); hits = int(top["label"].sum())
        ps.append(hits/k)
        if actual: rs.append(hits/actual)
    return float(np.mean(ps)), float(np.mean(rs)) if rs else 0.0


def random_split(df, frac, seed):
    ids = np.array(df["Citizen_ID"].unique(), dtype=object)
    rng = np.random.RandomState(seed); rng.shuffle(ids)
    n_test = max(1, int(len(ids)*frac))
    test_ids=set(ids[:n_test]); train_ids=set(ids[n_test:])
    return df[df.Citizen_ID.isin(train_ids)].copy(), df[df.Citizen_ID.isin(test_ids)].copy()


def state_holdout(df):
    states = sorted(df["State"].dropna().astype(str).unique())
    # Hold out two states deterministically, preferring states with sufficient rows.
    counts = df.groupby("State")["Citizen_ID"].nunique().sort_values(ascending=False)
    chosen = list(counts.index[:2]) if len(counts) >= 2 else states[:1]
    test = df[df.State.astype(str).isin([str(x) for x in chosen])].copy()
    train = df[~df.State.astype(str).isin([str(x) for x in chosen])].copy()
    return train, test, [str(x) for x in chosen]


def run_experiment(df, name, train, test, extra=None):
    out=[]
    for model_name in ["LogisticRegression", "DecisionTree", "RandomForest"]:
        m=pipeline(model_name); m.fit(train, train.label)
        pred=m.predict(test); proba=m.predict_proba(test)[:,1]
        p5,r5=ranking_metrics(test,proba)
        out.append({"dataset":name,"model":model_name,"train_citizens":int(train.Citizen_ID.nunique()),"test_citizens":int(test.Citizen_ID.nunique()),"train_records":len(train),"test_records":len(test),"accuracy":accuracy_score(test.label,pred),"precision":precision_score(test.label,pred,zero_division=0),"recall":recall_score(test.label,pred,zero_division=0),"f1_score":f1_score(test.label,pred,zero_division=0),"precision_at_5":p5,"recall_at_5":r5,"confusion_matrix":confusion_matrix(test.label,pred).tolist(),"extra":extra or {}})
    return out


def main():
    df=load_data(); experiments=[]
    tr,te=random_split(df,0.20,42); experiments += run_experiment(df,"random_80_20",tr,te)
    tr,te=random_split(df,0.30,43); experiments += run_experiment(df,"random_70_30",tr,te)
    tr,te=random_split(df,0.10,44); experiments += run_experiment(df,"random_90_10",tr,te)
    tr,te,states=state_holdout(df); experiments += run_experiment(df,"state_holdout",tr,te,{"held_out_states":states})
    outdir=os.path.join(os.path.dirname(Config.ML_MODEL_PATH),"experiments"); os.makedirs(outdir,exist_ok=True)
    with open(os.path.join(outdir,"results.json"),"w",encoding="utf-8") as f: json.dump({"source":Config.EXCEL_SOURCE_PATH,"experiments":experiments},f,indent=2)
    pd.DataFrame([{k:v for k,v in x.items() if k!="confusion_matrix"} for x in experiments]).to_csv(os.path.join(outdir,"results.csv"),index=False)
    summary=pd.DataFrame(experiments)
    best=summary.sort_values(["f1_score","precision_at_5"],ascending=False).iloc[0]
    print(summary[["dataset","model","accuracy","precision","recall","f1_score","precision_at_5","recall_at_5"]].to_string(index=False,float_format=lambda x:f"{x:.4f}"))
    print(f"\nBest experiment: {best.dataset} / {best.model} F1={best.f1_score:.4f}")
    print(f"Results: {outdir}")

if __name__=="__main__": main()
