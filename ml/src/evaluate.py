from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
from config.paths import ML_CACHE_DIR


def evaluate_model(city_id: str, X_test, y_test):
    model_path = os.path.join(ML_CACHE_DIR, f"{city_id}_rf_model.pkl")
    model = joblib.load(model_path)
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    return {"mae": mae, "r2": r2}
