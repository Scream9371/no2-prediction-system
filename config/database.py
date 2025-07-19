from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# MySQL不需要check_same_thread参数（这是SQLite特有的）
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
