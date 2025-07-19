from sqlalchemy.orm import Session
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
}


def create_no2_record(db: Session, record_data: dict, city_name: str = None):
    """
    创建NO2记录
    
    Args:
        db: 数据库会话
        record_data: 记录数据字典
        city_name: 城市名称，用于选择对应的数据表模型
        
    Returns:
        创建的记录对象
    """
    if city_name and city_name in CITY_MODEL_MAP:
        model_class = CITY_MODEL_MAP[city_name]
        record = model_class(**record_data)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    else:
        raise ValueError(f"不支持的城市: {city_name}")


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
