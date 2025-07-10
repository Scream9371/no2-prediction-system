from api.heweather.client import HeWeatherClient
from api.heweather.data_parser import parse_air_quality
from database.crud import create_no2_record
from database.session import get_db
from config.settings import settings

from sqlalchemy.orm import Session
from datetime import datetime

CITY_LIST = ["广州", "深圳", "珠海", "佛山", "惠州", "东莞", "中山", "江门", "肇庆"]


def collect_and_store():
    client = HeWeatherClient()
    db_gen = get_db()
    db = next(db_gen)
    for city in CITY_LIST:
        city_id = client.get_city_id(city)
        air_data = client.get_air_quality(city_id)
        parsed = parse_air_quality(air_data)
        if parsed:
            record_data = {
                "city_id": city_id,
                "city_name": city,
                "datetime": datetime.now(),
                **parsed,
            }
            create_no2_record(db, record_data)
    db.close()
