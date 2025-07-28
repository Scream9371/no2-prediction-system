import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 训练管道缓存目录 (scripts/run_pipeline.py)
ML_CACHE_DIR = os.path.join(DATA_DIR, "ml_cache")
PIPELINE_SCALERS_DIR = os.path.join(ML_CACHE_DIR, "scalers")

# 控制脚本缓存目录 (ml/src/control.py)
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
CONTROL_CACHE_DIR = os.path.join(OUTPUTS_DIR, "ml_cache")
CONTROL_SCALERS_DIR = os.path.join(CONTROL_CACHE_DIR, "scalers")
CONTROL_MODELS_DIR = os.path.join(OUTPUTS_DIR, "models")

# 训练管道模型目录
MODELS_DIR = os.path.join(BASE_DIR, "ml", "models")
DAILY_MODELS_DIR = os.path.join(MODELS_DIR, "daily")
LATEST_MODELS_DIR = os.path.join(MODELS_DIR, "latest")

# 其他目录
BACKUP_DIR = os.path.join(DATA_DIR, "backup")

# Web API 预测文件目录
WEB_PREDICTIONS_DIR = os.path.join(DATA_DIR, "predictions")

# 控制脚本预测文件目录
CONTROL_PREDICTIONS_DIR = os.path.join(OUTPUTS_DIR, "predictions")


def get_pipeline_scaler_path(city: str) -> str:
    """
    获取训练管道的城市特定标准化器路径
    
    Args:
        city (str): 城市名称
        
    Returns:
        str: 标准化器文件路径
    """
    return os.path.join(PIPELINE_SCALERS_DIR, f"{city}_scalers.pkl")


def get_control_scaler_path(city: str) -> str:
    """
    获取控制脚本的城市特定标准化器路径
    
    Args:
        city (str): 城市名称
        
    Returns:
        str: 标准化器文件路径
    """
    return os.path.join(CONTROL_SCALERS_DIR, f"{city}_scalers.pkl")


def get_daily_model_path(city: str, date_str: str) -> str:
    """
    获取日期版本模型路径
    
    Args:
        city (str): 城市名称
        date_str (str): 日期字符串 (YYYYMMDD)
        
    Returns:
        str: 日期版本模型路径
    """
    return os.path.join(DAILY_MODELS_DIR, f"{city}_{date_str}.pth")


def get_latest_model_path(city: str) -> str:
    """
    获取最新模型路径
    
    Args:
        city (str): 城市名称
        
    Returns:
        str: 最新模型路径
    """
    return os.path.join(LATEST_MODELS_DIR, f"{city}_latest.pth")


def get_control_model_path(city: str) -> str:
    """
    获取控制脚本模型路径
    
    Args:
        city (str): 城市名称
        
    Returns:
        str: 控制脚本模型路径
    """
    return os.path.join(CONTROL_MODELS_DIR, f"{city}_nc_cqr_model.pth")


def get_web_prediction_image_path(city: str, timestamp: str) -> str:
    """
    获取Web API预测图像文件路径
    
    Args:
        city (str): 城市名称
        timestamp (str): 时间戳字符串 (YYYYMMDD_HHMMSS)
        
    Returns:
        str: Web预测图像文件路径
    """
    return os.path.join(WEB_PREDICTIONS_DIR, f"{city}_web_prediction_{timestamp}.png")


def get_web_prediction_csv_path(city: str, timestamp: str) -> str:
    """
    获取Web API预测CSV文件路径
    
    Args:
        city (str): 城市名称
        timestamp (str): 时间戳字符串 (YYYYMMDD_HHMMSS)
        
    Returns:
        str: Web预测CSV文件路径
    """
    return os.path.join(WEB_PREDICTIONS_DIR, f"{city}_web_prediction_{timestamp}.csv")


def get_control_prediction_image_path(city: str, timestamp: str) -> str:
    """
    获取控制脚本预测图像文件路径
    
    Args:
        city (str): 城市名称
        timestamp (str): 时间戳字符串 (YYYYMMDD_HHMMSS)
        
    Returns:
        str: 控制脚本预测图像文件路径
    """
    control_predictions_dir = os.path.join(OUTPUTS_DIR, "predictions")
    return os.path.join(control_predictions_dir, f"{city}_nc_cqr_prediction_{timestamp}.png")


def get_control_prediction_csv_path(city: str, timestamp: str) -> str:
    """
    获取控制脚本预测CSV文件路径
    
    Args:
        city (str): 城市名称
        timestamp (str): 时间戳字符串 (YYYYMMDD_HHMMSS)
        
    Returns:
        str: 控制脚本预测CSV文件路径
    """
    control_predictions_dir = os.path.join(OUTPUTS_DIR, "predictions")
    return os.path.join(control_predictions_dir, f"{city}_nc_cqr_prediction_{timestamp}.csv")


def ensure_directories():
    """
    确保所有必要的目录存在
    """
    directories = [
        # 训练管道目录
        ML_CACHE_DIR, PIPELINE_SCALERS_DIR,
        MODELS_DIR, DAILY_MODELS_DIR, LATEST_MODELS_DIR,
        # 控制脚本目录
        OUTPUTS_DIR, CONTROL_CACHE_DIR, CONTROL_SCALERS_DIR, CONTROL_MODELS_DIR,
        # 控制脚本预测文件目录
        CONTROL_PREDICTIONS_DIR,
        # 其他目录
        BACKUP_DIR,
        # Web API预测文件目录
        WEB_PREDICTIONS_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
