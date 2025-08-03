from sqlalchemy.orm import Session
from datetime import datetime
from .models import (
    GuangzhouNO2Record, ShenzhenNO2Record, ZhuhaiNO2Record, FoshanNO2Record,
    HuizhouNO2Record, DongguanNO2Record, ZhongshanNO2Record, JiangmenNO2Record,
    ZhaoqingNO2Record, HongkongNO2Record, MacaoNO2Record
)

# 城市名称到模型的映射
CITY_MODEL_MAP = {
    "广州": GuangzhouNO2Record,
    "深圳": ShenzhenNO2Record,
    "珠海": ZhuhaiNO2Record,
    "佛山": FoshanNO2Record,
    "惠州": HuizhouNO2Record,
    "东莞": DongguanNO2Record,
    "中山": ZhongshanNO2Record,
    "江门": JiangmenNO2Record,
    "肇庆": ZhaoqingNO2Record,
    "香港": HongkongNO2Record,
    "澳门": MacaoNO2Record,
    # 支持完整的特别行政区名称
    "香港特别行政区": HongkongNO2Record,
    "澳门特别行政区": MacaoNO2Record,
}


def create_no2_record(db: Session, record_data: dict, city_name: str = None):
    """
    创建NO2记录（仅当指定时间不存在记录时）
    
    以观测时间为索引，如果相同时间的记录已存在则跳过插入，避免重复数据。
    
    Args:
        db: 数据库会话
        record_data: 记录数据字典，必须包含observation_time字段
        city_name: 城市名称，用于选择对应的数据表模型
        
    Returns:
        创建的记录对象或已存在的记录对象
    """
    if not city_name or city_name not in CITY_MODEL_MAP:
        raise ValueError(f"不支持的城市: {city_name}")
    
    observation_time = record_data.get('observation_time')
    if not observation_time:
        raise ValueError("记录数据必须包含observation_time字段")
    
    model_class = CITY_MODEL_MAP[city_name]
    
    # 检查是否已存在相同时间的记录
    existing_record = db.query(model_class).filter(
        model_class.observation_time == observation_time
    ).first()
    
    if existing_record:
        return existing_record
    
    # 创建新记录
    record = model_class(**record_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_no2_records(db: Session, city_name: str, limit: int = 100):
    """
    获取指定城市的NO2记录
    
    Args:
        db: 数据库会话
        city_name: 城市名称
        limit: 返回记录数量限制
        
    Returns:
        记录列表
    """
    if city_name in CITY_MODEL_MAP:
        model_class = CITY_MODEL_MAP[city_name]
        return (
            db.query(model_class)
            .order_by(model_class.observation_time.desc())
            .limit(limit)
            .all()
        )
    else:
        raise ValueError(f"不支持的城市: {city_name}")


