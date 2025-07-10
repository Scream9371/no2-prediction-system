from database.models import Base
from config.database import engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成")
