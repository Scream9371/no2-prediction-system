from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import os
from dotenv import load_dotenv

from .models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 确保数据库存在
if not database_exists(engine.url):
    create_database(engine.url)

# 创建所有表
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
