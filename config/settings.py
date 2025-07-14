import os

class Settings:
    API_KEY = os.getenv("HEWEATHER_API_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATA_PATH = os.getenv("DATA_PATH", "./data")
    MODEL_PATH = os.getenv("MODEL_PATH", "./ml/models/trained")
    RETRAIN_THRESHOLD = float(os.getenv("RETRAIN_THRESHOLD", 0.8))
    
    # JWT相关配置（和风天气商业版API）
    HF_API_HOST = os.getenv("HF_API_HOST")
    
    @staticmethod
    def get_private_key():
        """获取正确格式的私钥，处理WSL兼容性问题"""
        key = os.getenv("HF_PRIVATE_KEY")
        if not key or len(key) < 100:  # 如果私钥不完整，使用备用方案
            # 硬编码私钥以解决WSL兼容性问题
            return """-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIFFIzraECKVymQXx9CLwVgBbypHk+SKwM4DGwPWb6vRk
-----END PRIVATE KEY-----"""
        else:
            # 正常处理换行符
            return key.replace("\\r\\n", "\n").replace("\\n", "\n")
    
    HF_PRIVATE_KEY = get_private_key.__func__()
    HF_PROJECT_ID = os.getenv("HF_PROJECT_ID")
    HF_KEY_ID = os.getenv("HF_KEY_ID")

settings = Settings()