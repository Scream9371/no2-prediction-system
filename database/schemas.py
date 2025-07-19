from pydantic import BaseModel
from datetime import datetime


class NO2RecordSchema(BaseModel):
    id: int
    observation_time: datetime  # ISO8601:2004格式
    no2_concentration: float  # μg/m³
    temperature: float  # 摄氏度
    humidity: float  # 相对湿度(%)
    wind_speed: float  # 风速(km/h)
    wind_direction: float  # 风向(360度)
    pressure: float  # 大气压(hPa)

    class Config:
        from_attributes = True  # 新版pydantic推荐使用from_attributes替代orm_mode
