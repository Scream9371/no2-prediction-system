from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database.models import Base
from database.db import engine
from api.heweather.client import HeWeatherClient
from datetime import datetime, timedelta


def init_database():
    """初始化数据库:删除所有表并重新创建"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def fetch_historical_data():
    """从和风天气API获取过去10天的数据"""
    client = HeWeatherClient()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)

    # TODO: 实现数据获取逻辑
    pass


if __name__ == "__main__":
    load_dotenv()
    print("正在初始化数据库...")
    init_database()
    print("正在获取历史数据...")
    fetch_historical_data()
    print("数据库设置完成!")
