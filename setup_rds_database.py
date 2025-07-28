#!/usr/bin/env python3
"""
阿里云RDS数据库初始化脚本
配置RDS MySQL数据库用于NO2预测系统
"""
import os
import sys
import time
import mysql.connector
from mysql.connector import Error

# RDS配置信息
RDS_CONFIG = {
    'host': 'rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com',
    'port': 3306,
    'user': 'root',  # 请替换为您的RDS主账户用户名
    'password': '',  # 请替换为您的RDS主账户密码
    'charset': 'utf8mb4',
    'autocommit': True
}

# 应用数据库配置
APP_DB_CONFIG = {
    'database': 'no2_prediction',
    'user': 'no2user',
    'password': 'NO2User2025!',
    'description': 'NO2预测系统专用数据库用户'
}

def test_rds_connection():
    """测试RDS连接"""
    print("🔗 测试RDS数据库连接...")
    
    try:
        connection = mysql.connector.connect(
            host=RDS_CONFIG['host'],
            port=RDS_CONFIG['port'],
            user=RDS_CONFIG['user'],
            password=RDS_CONFIG['password']
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ RDS连接成功！MySQL版本: {version[0]}")
            cursor.close()
            connection.close()
            return True
            
    except Error as e:
        print(f"❌ RDS连接失败: {e}")
        print("请检查以下配置:")
        print(f"  - RDS地址: {RDS_CONFIG['host']}")
        print(f"  - 端口: {RDS_CONFIG['port']}")
        print(f"  - 用户名: {RDS_CONFIG['user']}")
        print(f"  - 密码: {'*' * len(RDS_CONFIG['password']) if RDS_CONFIG['password'] else '(未设置)'}")
        return False

def create_application_database():
    """创建应用数据库和用户"""
    print("🗄️ 创建应用数据库和用户...")
    
    try:
        # 连接到RDS
        connection = mysql.connector.connect(**RDS_CONFIG)
        cursor = connection.cursor()
        
        # 创建数据库
        print(f"  创建数据库: {APP_DB_CONFIG['database']}")
        cursor.execute(f"""
            CREATE DATABASE IF NOT EXISTS {APP_DB_CONFIG['database']} 
            CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        
        # 创建应用用户
        print(f"  创建应用用户: {APP_DB_CONFIG['user']}")
        cursor.execute(f"""
            CREATE USER IF NOT EXISTS '{APP_DB_CONFIG['user']}'@'%' 
            IDENTIFIED BY '{APP_DB_CONFIG['password']}'
        """)
        
        # 授予权限
        print(f"  授予数据库权限...")
        cursor.execute(f"""
            GRANT ALL PRIVILEGES ON {APP_DB_CONFIG['database']}.* 
            TO '{APP_DB_CONFIG['user']}'@'%'
        """)
        
        # 刷新权限
        cursor.execute("FLUSH PRIVILEGES")
        
        print("✅ 数据库和用户创建成功!")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"❌ 数据库创建失败: {e}")
        return False

def test_application_connection():
    """测试应用用户连接"""
    print("🧪 测试应用用户连接...")
    
    try:
        app_config = RDS_CONFIG.copy()
        app_config.update({
            'user': APP_DB_CONFIG['user'],
            'password': APP_DB_CONFIG['password'],
            'database': APP_DB_CONFIG['database']
        })
        
        connection = mysql.connector.connect(**app_config)
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # 测试基本操作
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"✅ 应用用户连接成功!")
            print(f"  当前数据库: {db_name}")
            print(f"  现有表数量: {len(tables)}")
            
            cursor.close()
            connection.close()
            return True
            
    except Error as e:
        print(f"❌ 应用用户连接失败: {e}")
        return False

def initialize_tables():
    """初始化数据表"""
    print("📋 初始化应用数据表...")
    
    try:
        # 添加项目路径
        sys.path.insert(0, '.')
        
        # 设置环境变量
        os.environ['DATABASE_URL'] = f"mysql+pymysql://{APP_DB_CONFIG['user']}:{APP_DB_CONFIG['password']}@{RDS_CONFIG['host']}:{RDS_CONFIG['port']}/{APP_DB_CONFIG['database']}"
        
        # 初始化数据库表
        from database.session import init_database
        
        if init_database():
            print("✅ 数据表初始化成功!")
            return True
        else:
            print("⚠️ 数据表可能已存在")
            return True
            
    except Exception as e:
        print(f"❌ 数据表初始化失败: {e}")
        print("💡 数据表将在应用首次启动时自动创建")
        return False

def generate_env_config():
    """生成环境配置"""
    print("⚙️ 生成环境配置...")
    
    database_url = f"mysql+pymysql://{APP_DB_CONFIG['user']}:{APP_DB_CONFIG['password']}@{RDS_CONFIG['host']}:{RDS_CONFIG['port']}/{APP_DB_CONFIG['database']}"
    
    env_content = f"""# NO2预测系统 - RDS云数据库配置
# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

# 生产环境配置
FLASK_ENV=production
SECRET_KEY=aliyun-rds-no2-prediction-2025

# 阿里云RDS数据库配置
DATABASE_URL={database_url}

# 和风天气API配置（可选）
# HF_API_HOST=your_api_host
# HF_PROJECT_ID=your_project_id
# HF_KEY_ID=your_credential_id

# 服务器配置
SERVER_IP=8.136.12.26
PORT=5000

# RDS配置信息（用于备份和管理）
RDS_HOST={RDS_CONFIG['host']}
RDS_PORT={RDS_CONFIG['port']}
RDS_DATABASE={APP_DB_CONFIG['database']}
RDS_USER={APP_DB_CONFIG['user']}
"""
    
    # 保存到.env文件
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 环境配置文件已生成 (.env)")
    print(f"  数据库地址: {RDS_CONFIG['host']}")
    print(f"  数据库名: {APP_DB_CONFIG['database']}")
    print(f"  应用用户: {APP_DB_CONFIG['user']}")

def main():
    """主函数"""
    print("🚀 阿里云RDS数据库初始化")
    print("=" * 60)
    print(f"RDS地址: {RDS_CONFIG['host']}")
    print(f"端口: {RDS_CONFIG['port']}")
    print("=" * 60)
    
    # 检查RDS配置
    if not RDS_CONFIG['password']:
        print("❌ 请先配置RDS主账户密码!")
        print("编辑此脚本，在RDS_CONFIG中设置'password'字段")
        return False
    
    # 执行初始化步骤
    steps = [
        ("测试RDS连接", test_rds_connection),
        ("创建应用数据库", create_application_database),
        ("测试应用用户连接", test_application_connection),
        ("初始化数据表", initialize_tables),
        ("生成环境配置", generate_env_config)
    ]
    
    success_count = 0
    for step_name, step_func in steps:
        print(f"\n📌 {step_name}...")
        try:
            if step_func():
                success_count += 1
            else:
                print(f"⚠️ {step_name} 未完全成功")
        except Exception as e:
            print(f"❌ {step_name} 执行出错: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    if success_count >= 4:  # 至少前4步成功
        print("🎉 RDS数据库配置成功!")
        print(f"✅ 完成步骤: {success_count}/{len(steps)}")
        print(f"\n📊 配置摘要:")
        print(f"  RDS地址: {RDS_CONFIG['host']}")
        print(f"  数据库: {APP_DB_CONFIG['database']}")
        print(f"  用户: {APP_DB_CONFIG['user']}")
        print(f"  连接字符串: mysql+pymysql://{APP_DB_CONFIG['user']}:***@{RDS_CONFIG['host']}:{RDS_CONFIG['port']}/{APP_DB_CONFIG['database']}")
        
        print(f"\n🔄 下一步:")
        print(f"  1. 运行部署脚本: sudo ./deploy_aliyun_ecs_rds.sh")
        print(f"  2. 或继续手动配置应用服务")
        
        return True
    else:
        print("❌ RDS配置遇到问题")
        print(f"完成步骤: {success_count}/{len(steps)}")
        print("请检查配置信息并重试")
        return False

if __name__ == "__main__":
    try:
        # 安装必要的依赖
        import mysql.connector
    except ImportError:
        print("❌ 缺少mysql-connector-python依赖")
        print("请在虚拟环境中运行:")
        print("  ./venv/bin/python setup_rds_database.py")
        print("或先安装依赖:")
        print("  ./venv/bin/pip install mysql-connector-python")
        sys.exit(1)
    
    main()