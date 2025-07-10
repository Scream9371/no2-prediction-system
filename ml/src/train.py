import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
from config.paths import ML_CACHE_DIR
from .data_loader import load_data_from_db
from .data_processing import clean_and_engineer_features, standardize_features
from sqlalchemy.orm import Session


def train_model(db: Session, city_id: str):
    df = load_data_from_db(db, city_id)
    df = clean_and_engineer_features(df)
    features = df[["pm25", "temperature", "humidity", "wind_speed"]]
    target = df["no2"]
    features = standardize_features(features, fit=True)
    model = RandomForestRegressor()
    model.fit(features, target)
    model_path = os.path.join(ML_CACHE_DIR, f"{city_id}_rf_model.pkl")
    joblib.dump(model, model_path)
    return model_path
