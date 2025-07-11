import os

class Settings:
    API_KEY = os.getenv("HEWEATHER_API_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATA_PATH = os.getenv("DATA_PATH", "./data")
    MODEL_PATH = os.getenv("MODEL_PATH", "./ml/models/trained")
    RETRAIN_THRESHOLD = float(os.getenv("RETRAIN_THRESHOLD", 0.8))
    
    # JWT相关配置（和风天气商业版API）
    HF_API_HOST = os.getenv("HF_API_HOST")
    HF_PRIVATE_KEY = os.getenv("HF_PRIVATE_KEY")
    HF_PROJECT_ID = os.getenv("HF_PROJECT_ID")
    HF_KEY_ID = os.getenv("HF_KEY_ID")

settings = Settings()