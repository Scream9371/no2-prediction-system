from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NO2Record(Base):
    __tablename__ = "no2_records"
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(String, index=True)
    city_name = Column(String)
    datetime = Column(DateTime, index=True)
    no2 = Column(Float)
    pm25 = Column(Float)
    temperature = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    weather = Column(String)
