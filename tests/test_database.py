import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import *


@pytest.fixture
def db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def test_create_record(db: Session):
    """测试创建记录"""
    # 创建测试数据
    test_data = {
        "observation_time": datetime.now(),
        "no2_concentration": 45.0,
        "temperature": 25.0,
        "humidity": 80.0,
        "wind_speed": 15.0,
        "wind_direction": 180.0,
        "pressure": 1013.0,
    }

    # 为广州创建记录
    record = GuangzhouNO2Record(**test_data)
    db.add(record)
    db.commit()

    # 验证记录
    saved_record = db.query(GuangzhouNO2Record).first()
    assert saved_record is not None
    assert saved_record.no2_concentration == 45.0
