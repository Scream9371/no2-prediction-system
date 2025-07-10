from pydantic import BaseModel
from datetime import datetime


class NO2RecordSchema(BaseModel):
    id: int
    city_id: str
    city_name: str
    datetime: datetime
    no2: float
    pm25: float
    temperature: float
    humidity: float
    wind_speed: float
    weather: str

    class Config:
        orm_mode = True
