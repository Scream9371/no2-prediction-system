"""
数据预处理模块 - NC-CQR数据预处理与特征工程
"""
import os
from typing import Tuple, Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


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


def save_scalers_for_pipeline(scalers: Dict, city: str) -> str:
    """
    保存训练管道的标准化器（按城市分离）
    
    Args:
        scalers (Dict): 标准化器字典
        city (str): 城市名称
        
    Returns:
        str: 保存路径
    """
    from config.paths import get_pipeline_scaler_path, ensure_directories

    ensure_directories()
    scaler_path = get_pipeline_scaler_path(city)

    # 原子性操作：先写临时文件，再重命名
    temp_path = scaler_path + ".tmp"
    joblib.dump(scalers, temp_path)

    # Windows系统需要先删除目标文件
    if os.path.exists(scaler_path):
        os.remove(scaler_path)
    os.rename(temp_path, scaler_path)

    return scaler_path


def save_scalers_for_control(scalers: Dict, city: str) -> str:
    """
    保存控制脚本的标准化器（按城市分离）
    
    Args:
        scalers (Dict): 标准化器字典
        city (str): 城市名称
        
    Returns:
        str: 保存路径
    """
    from config.paths import get_control_scaler_path, ensure_directories

    ensure_directories()
    scaler_path = get_control_scaler_path(city)

    # 原子性操作：先写临时文件，再重命名
    temp_path = scaler_path + ".tmp"
    joblib.dump(scalers, temp_path)

    # Windows系统需要先删除目标文件
    if os.path.exists(scaler_path):
        os.remove(scaler_path)
    os.rename(temp_path, scaler_path)

    return scaler_path
