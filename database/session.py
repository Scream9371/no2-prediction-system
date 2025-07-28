"""
数据库会话管理模块
提供数据库连接和会话管理功能
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# 数据库配置
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./no2_prediction.db')

# 创建引擎
try:
    if DATABASE_URL.startswith('mysql'):
        # MySQL配置
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
    else:
        # SQLite配置（开发环境）
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False
        )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
except Exception as e:
    print(f"数据库引擎创建失败: {e}")
    engine = None
    SessionLocal = None

def get_db():
    """原有的数据库会话获取函数（保持兼容性）"""
    if SessionLocal is None:
        yield None
        return
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """
    获取数据库会话的上下文管理器
    
    Yields:
        Session: 数据库会话对象
    """
    if SessionLocal is None:
        yield None
        return
        
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        print(f"数据库操作错误: {e}")
        raise
    finally:
        session.close()

def init_database():
    """
    初始化数据库表结构
    
    Returns:
        bool: 初始化是否成功
    """
    if engine is None:
        print("数据库引擎未初始化")
        return False
        
    try:
        # 导入所有模型以确保表结构被注册
        from database.models import Base
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("数据库表结构初始化成功")
        return True
        
    except Exception as e:
        print(f"数据库表结构初始化失败: {e}")
        return False

def test_database_connection():
    """
    测试数据库连接
    
    Returns:
        bool: 连接是否成功
    """
    if engine is None:
        return False
        
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"数据库连接测试失败: {e}")
        return False
