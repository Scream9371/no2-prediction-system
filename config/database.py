from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
from config.settings import settings

# MySQL不需要check_same_thread参数（这是SQLite特有的）
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_database_exists():
    """
    确保数据库存在，如果不存在则自动创建
    
    Returns:
        bool: 数据库是否新创建
    """
    if not database_exists(engine.url):
        create_database(engine.url)
        return True
    return False
