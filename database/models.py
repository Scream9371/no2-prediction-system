from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NO2RecordBase:
    """NO2记录的基础模型类"""

    id = Column(Integer, primary_key=True)
    observation_time = Column(DateTime, nullable=False)  # ISO8601:2004格式
    no2_concentration = Column(Float, nullable=False)  # μg/m³
    temperature = Column(Float, nullable=False)  # 摄氏度
    humidity = Column(Float, nullable=False)  # 相对湿度(%)
    wind_speed = Column(Float, nullable=False)  # 风速(km/h)
    wind_direction = Column(Float, nullable=False)  # 风向(360度)
    pressure = Column(Float, nullable=False)  # 大气压(hPa)


# 为每个城市创建对应的数据表模型
class GuangzhouNO2Record(Base, NO2RecordBase):
    __tablename__ = "guangzhou_no2_records"


class ShenzhenNO2Record(Base, NO2RecordBase):
    __tablename__ = "shenzhen_no2_records"


class ZhuhaiNO2Record(Base, NO2RecordBase):
    __tablename__ = "zhuhai_no2_records"


class FoshanNO2Record(Base, NO2RecordBase):
    __tablename__ = "foshan_no2_records"


class HuizhouNO2Record(Base, NO2RecordBase):
    __tablename__ = "huizhou_no2_records"


class DongguanNO2Record(Base, NO2RecordBase):
    __tablename__ = "dongguan_no2_records"


class ZhongshanNO2Record(Base, NO2RecordBase):
    __tablename__ = "zhongshan_no2_records"


class JiangmenNO2Record(Base, NO2RecordBase):
    __tablename__ = "jiangmen_no2_records"


class ZhaoqingNO2Record(Base, NO2RecordBase):
    __tablename__ = "zhaoqing_no2_records"


class HongkongNO2Record(Base, NO2RecordBase):
    __tablename__ = "hongkong_no2_records"


class MacaoNO2Record(Base, NO2RecordBase):
    __tablename__ = "macao_no2_records"
