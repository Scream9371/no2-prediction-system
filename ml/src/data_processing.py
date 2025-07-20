"""
数据预处理模块 - NC-CQR数据预处理与特征工程
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Dict
import os
import joblib


def prepare_nc_cqr_data(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    NC-CQR数据预处理与特征工程
    
    Args:
        df (pd.DataFrame): 原始数据，包含observation_time, no2等字段
        
    Returns:
        Tuple[np.ndarray, np.ndarray, Dict]: 特征矩阵X, 目标变量y, 标准化器字典
    """
    # 确保observation_time是datetime类型
    if not pd.api.types.is_datetime64_any_dtype(df['observation_time']):
        df['observation_time'] = pd.to_datetime(df['observation_time'])
    
    # 时间特征工程
    df['hour'] = df['observation_time'].dt.hour
    df['day_of_week'] = df['observation_time'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # 风向的周期性编码
    df['wind_sin'] = np.sin(np.radians(df['wind_direction']))
    df['wind_cos'] = np.cos(np.radians(df['wind_direction']))
    
    # 滞后特征 - NO2浓度的历史值
    df['no2_lag1'] = df['no2'].shift(1)
    df['no2_lag2'] = df['no2'].shift(2)
    
    # 删除由于滞后特征产生的NaN值
    df = df.dropna().reset_index(drop=True)
    
    # 定义特征列
    feature_cols = [
        'temperature', 'humidity', 'wind_speed', 'pressure',
        'wind_sin', 'wind_cos',
        'no2_lag1', 'no2_lag2',
        'hour', 'day_of_week', 'is_weekend'
    ]
    
    # 标准化连续变量
    scalers = {}
    for col in ['temperature', 'humidity', 'wind_speed', 'pressure']:
        scaler = StandardScaler()
        df[col] = scaler.fit_transform(df[[col]])
        scalers[col] = scaler
    
    # 构建特征矩阵和目标变量
    X = df[feature_cols].values
    y = df['no2'].values
    
    return X, y, scalers


def create_time_features(datetime_series: pd.Series) -> pd.DataFrame:
    """
    从时间序列创建时间特征
    
    Args:
        datetime_series (pd.Series): 时间序列
        
    Returns:
        pd.DataFrame: 时间特征DataFrame
    """
    features = pd.DataFrame()
    features['hour'] = datetime_series.dt.hour
    features['day_of_week'] = datetime_series.dt.dayofweek
    features['is_weekend'] = features['day_of_week'].isin([5, 6]).astype(int)
    features['hour_sin'] = np.sin(2 * np.pi * features['hour'] / 24)
    features['hour_cos'] = np.cos(2 * np.pi * features['hour'] / 24)
    features['day_sin'] = np.sin(2 * np.pi * features['day_of_week'] / 7)
    features['day_cos'] = np.cos(2 * np.pi * features['day_of_week'] / 7)
    
    return features


def encode_wind_direction(wind_direction: pd.Series) -> pd.DataFrame:
    """
    风向的周期性编码
    
    Args:
        wind_direction (pd.Series): 风向角度(0-360)
        
    Returns:
        pd.DataFrame: 编码后的风向特征
    """
    wind_features = pd.DataFrame()
    wind_features['wind_sin'] = np.sin(np.radians(wind_direction))
    wind_features['wind_cos'] = np.cos(np.radians(wind_direction))
    
    return wind_features


def create_lag_features(series: pd.Series, lags: list = [1, 2]) -> pd.DataFrame:
    """
    创建滞后特征
    
    Args:
        series (pd.Series): 原始时间序列
        lags (list): 滞后期数列表
        
    Returns:
        pd.DataFrame: 滞后特征DataFrame
    """
    lag_features = pd.DataFrame()
    for lag in lags:
        lag_features[f'{series.name}_lag{lag}'] = series.shift(lag)
    
    return lag_features


def save_scalers(scalers: Dict, cache_dir: str = "data/ml_cache") -> str:
    """
    保存标准化器
    
    Args:
        scalers (Dict): 标准化器字典
        cache_dir (str): 缓存目录
        
    Returns:
        str: 保存路径
    """
    os.makedirs(cache_dir, exist_ok=True)
    scaler_path = os.path.join(cache_dir, "nc_cqr_scalers.pkl")
    joblib.dump(scalers, scaler_path)
    return scaler_path


def load_scalers(cache_dir: str = "data/ml_cache") -> Dict:
    """
    加载标准化器
    
    Args:
        cache_dir (str): 缓存目录
        
    Returns:
        Dict: 标准化器字典
    """
    scaler_path = os.path.join(cache_dir, "nc_cqr_scalers.pkl")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"标准化器文件未找到: {scaler_path}")
    
    return joblib.load(scaler_path)


def clean_and_engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    数据清洗和基础特征工程
    
    Args:
        df (pd.DataFrame): 原始数据
        
    Returns:
        pd.DataFrame: 清洗后的数据
    """
    # 删除缺失值
    df = df.dropna()
    
    # 数据类型转换
    numeric_cols = ['no2', 'temperature', 'humidity', 'wind_speed', 'pressure', 'wind_direction']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 移除异常值（可根据需要调整）
    for col in numeric_cols:
        if col in df.columns:
            Q1 = df[col].quantile(0.01)
            Q3 = df[col].quantile(0.99)
            df = df[(df[col] >= Q1) & (df[col] <= Q3)]
    
    return df.reset_index(drop=True)


def standardize_features(df: pd.DataFrame, feature_cols: list, 
                        fit: bool = True, scalers: Dict = None) -> Tuple[pd.DataFrame, Dict]:
    """
    标准化指定特征
    
    Args:
        df (pd.DataFrame): 数据
        feature_cols (list): 需要标准化的特征列
        fit (bool): 是否拟合标准化器
        scalers (Dict): 预训练的标准化器
        
    Returns:
        Tuple[pd.DataFrame, Dict]: 标准化后的数据, 标准化器字典
    """
    df_scaled = df.copy()
    
    if fit:
        scalers = {}
        for col in feature_cols:
            if col in df.columns:
                scaler = StandardScaler()
                df_scaled[col] = scaler.fit_transform(df[[col]])
                scalers[col] = scaler
    else:
        if scalers is None:
            raise ValueError("预测模式下必须提供预训练的标准化器")
        
        for col in feature_cols:
            if col in df.columns and col in scalers:
                df_scaled[col] = scalers[col].transform(df[[col]])
    
    return df_scaled, scalers