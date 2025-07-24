from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database.models import Base
from database.db import engine


def init_database():
    """初始化数据库:删除所有表并重新创建"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)



if __name__ == "__main__":
    load_dotenv()
    print("正在初始化数据库...")
    init_database()
    print("数据库设置完成!")
