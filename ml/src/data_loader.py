"""
数据加载器模块 - 从MySQL数据库加载NO2数据
"""
import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    GuangzhouNO2Record, ShenzhenNO2Record, ZhuhaiNO2Record, FoshanNO2Record,
    HuizhouNO2Record, DongguanNO2Record, ZhongshanNO2Record, JiangmenNO2Record,
    ZhaoqingNO2Record, HongkongNO2Record, MacaoNO2Record
)

# 城市名到模型类的映射
CITY_MODEL_MAP = {
    'guangzhou': GuangzhouNO2Record,
    'shenzhen': ShenzhenNO2Record,
    'zhuhai': ZhuhaiNO2Record,
    'foshan': FoshanNO2Record,
    'huizhou': HuizhouNO2Record,
    'dongguan': DongguanNO2Record,
    'zhongshan': ZhongshanNO2Record,
    'jiangmen': JiangmenNO2Record,
    'zhaoqing': ZhaoqingNO2Record,
    'hongkong': HongkongNO2Record,
    'macao': MacaoNO2Record
}


def load_data_from_mysql(city: str = 'dongguan') -> pd.DataFrame:
    """
    从MySQL数据库加载指定城市的NO2数据
    
    Args:
        city (str): 城市名称，默认为'dongguan'
        
    Returns:
        pd.DataFrame: 包含NO2数据的DataFrame
        
    Raises:
        ValueError: 当城市不在支持列表中或数据库连接失败时
    """
    # 检查城市是否支持
    if city not in CITY_MODEL_MAP:
        raise ValueError(f"不支持的城市: {city}。支持的城市: {list(CITY_MODEL_MAP.keys())}")

    # 加载环境变量
    load_dotenv()

    # 获取数据库连接字符串
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("请在.env文件中设置DATABASE_URL环境变量")

    # 创建数据库连接
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 获取对应城市的模型类
        model_class = CITY_MODEL_MAP[city]

        # 计算30天前的时间点
        cutoff_time = datetime.now() - timedelta(days=30)

        # 查询最近30天(720小时)的数据
        query = session.query(model_class).filter(
            model_class.observation_time >= cutoff_time
        ).order_by(model_class.observation_time)
        records = query.all()

        if not records:
            raise ValueError(f"{city}_no2_records表中没有数据")

        # 转换为DataFrame
        data = []
        for record in records:
            data.append({
                'observation_time': record.observation_time,
                'no2': record.no2_concentration,
                'temperature': record.temperature,
                'humidity': record.humidity,
                'wind_speed': record.wind_speed,
                'wind_direction': record.wind_direction,
                'pressure': record.pressure
            })

        df = pd.DataFrame(data)
        print(f"成功从数据库加载 {len(df)} 条{city}NO2记录 (30天滑窗)")
        return df

    except Exception as e:
        raise ValueError(f"数据库操作失败: {str(e)}")
    finally:
        session.close()


def get_supported_cities() -> list:
    """
    获取支持的城市列表
    
    Returns:
        list: 支持的城市名称列表
    """
    return list(CITY_MODEL_MAP.keys())
