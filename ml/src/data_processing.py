import pandas as pd
from sklearn.preprocessing import StandardScaler
import os
import joblib
from config.paths import ML_CACHE_DIR


def clean_and_engineer_features(df: pd.DataFrame):
    df = df.dropna()
    # 可扩展更多特征工程
    return df


def standardize_features(df: pd.DataFrame, fit: bool = True, scaler_path: str = None):
    scaler_file = scaler_path or os.path.join(ML_CACHE_DIR, "scaler.pkl")
    if fit:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(df)
        joblib.dump(scaler, scaler_file)
    else:
        scaler = joblib.load(scaler_file)
        scaled = scaler.transform(df)
    return pd.DataFrame(scaled, columns=df.columns)
