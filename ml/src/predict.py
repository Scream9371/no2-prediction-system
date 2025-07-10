import pandas as pd
import numpy as np
import joblib
import os
from config.paths import ML_CACHE_DIR
from .data_processing import standardize_features


def predict_next_24h(city_id: str, features: pd.DataFrame):
    model_path = os.path.join(ML_CACHE_DIR, f"{city_id}_rf_model.pkl")
    scaler_path = os.path.join(ML_CACHE_DIR, "scaler.pkl")
    model = joblib.load(model_path)
    features = standardize_features(features, fit=False, scaler_path=scaler_path)
    preds = model.predict(features)
    # 置信区间可用模型残差的标准差估算
    std = np.std(preds)
    lower = preds - 1.96 * std
    upper = preds + 1.96 * std
    return preds, lower, upper
