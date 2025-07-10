import os

class Settings:
    API_KEY = os.getenv("HEWEATHER_API_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATA_PATH = os.getenv("DATA_PATH", "./data")
    MODEL_PATH = os.getenv("MODEL_PATH", "./ml/models/trained")
    RETRAIN_THRESHOLD = float(os.getenv("RETRAIN_THRESHOLD", 0.8))

settings = Settings()