from dotenv import load_dotenv

from config.database import engine, ensure_database_exists
from database.models import Base


def init_database():
    """初始化数据库:确保数据库存在并删除所有表，然后重新创建"""
    # 确保数据库存在
    database_created = ensure_database_exists()
    if database_created:
        print("数据库不存在，已自动创建")
    
    # 删除所有表并重新创建
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)



if __name__ == "__main__":
    load_dotenv()
    print("正在初始化数据库...")
    init_database()
    print("数据库设置完成!")
