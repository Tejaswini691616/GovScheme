# PATH: GovScheme/tools/train_production_model.py
"""Train the selected recommendation model on all available prototype data.

Model selection is based on citizen-level holdout experiments. After selection,
this script fits the selected DecisionTree on all 5,000 citizens / 100,000
citizen-scheme records for deployment. Evaluation metrics remain in
ml_models/experiments/results.json.
"""
import os, sys, joblib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai.train_model import load_merged_dataset, build_pipeline
from config import Config
from sklearn.tree import DecisionTreeClassifier

RANDOM_STATE=42

def main():
    df=load_merged_dataset()
    model=build_pipeline(DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE))
    model.fit(df, df['label'])
    os.makedirs(os.path.dirname(Config.ML_MODEL_PATH), exist_ok=True)
    joblib.dump({'pipeline':model,'model_name':'DecisionTree','training_records':len(df),'training_citizens':int(df.Citizen_ID.nunique())}, Config.ML_MODEL_PATH)
    print(f"Production model saved: {Config.ML_MODEL_PATH}")
    print(f"Training citizens: {df.Citizen_ID.nunique()}")
    print(f"Training records: {len(df)}")

if __name__=='__main__': main()
