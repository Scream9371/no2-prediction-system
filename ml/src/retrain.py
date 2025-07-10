from .train import train_model
from .evaluate import evaluate_model
from config.settings import settings
from sqlalchemy.orm import Session


def auto_retrain(db: Session, city_id: str, X_test, y_test):
    metrics = evaluate_model(city_id, X_test, y_test)
    if metrics["r2"] < settings.RETRAIN_THRESHOLD:
        train_model(db, city_id)
        return True
    return False
