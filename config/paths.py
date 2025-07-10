import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ML_CACHE_DIR = os.path.join(DATA_DIR, "ml_cache")
EXTERNAL_DATA_DIR = os.path.join(DATA_DIR, "external")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
