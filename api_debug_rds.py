"""
RDS数据库连接测试API
提供数据库状态检查和诊断功能
"""
import os
import time
from datetime import datetime
from flask import Blueprint, jsonify
import mysql.connector
from mysql.connector import Error

# 创建调试蓝图
debug_bp = Blueprint('debug_rds', __name__, url_prefix='/api/debug')

def get_rds_config():
    """从环境变量获取RDS配置"""
    database_url = os.environ.get('DATABASE_URL', '')
    
    if 'mysql+pymysql://' in database_url:
        # 解析连接字符串
        # mysql+pymysql://user:password@host:port/database
        url_parts = database_url.replace('mysql+pymysql://', '').split('/')
        db_name = url_parts[-1] if len(url_parts) > 1 else 'no2_prediction'
        
        auth_host = url_parts[0].split('@')
        if len(auth_host) == 2:
            auth_part = auth_host[0]
            host_port = auth_host[1]
            
            user_pass = auth_part.split(':')
            user = user_pass[0] if len(user_pass) > 0 else 'no2user'
            password = user_pass[1] if len(user_pass) > 1 else ''
            
            host_port_parts = host_port.split(':')
            host = host_port_parts[0] if len(host_port_parts) > 0 else 'localhost'
            port = int(host_port_parts[1]) if len(host_port_parts) > 1 else 3306
            
            return {
                'host': host,
                'port': port,
                'user': user,
                'password': password,
                'database': db_name
            }
    
    return None

@debug_bp.route('/database')
def test_database():
    """测试数据库连接状态"""
    config = get_rds_config()
    if not config:
        return jsonify({
            'status': 'error',
            'message': '无法解析数据库配置',
            'timestamp': datetime.now().isoformat()
        }), 500
    
    try:
        start_time = time.time()
        
        # 测试连接
        connection = mysql.connector.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            connect_timeout=10,
            autocommit=True
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # 获取数据库信息
            cursor.execute("SELECT VERSION()")
            mysql_version = cursor.fetchone()[0]
            
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_count = len(tables)
            
            # 测试查询性能
            cursor.execute("SELECT NOW()")
            server_time = cursor.fetchone()[0]
            
            connection_time = round((time.time() - start_time) * 1000, 2)
            
            cursor.close()
            connection.close()
            
            return jsonify({
                'status': 'success',
                'message': 'RDS数据库连接正常',
                'data': {
                    'host': config['host'],
                    'port': config['port'],
                    'database': current_db,
                    'mysql_version': mysql_version,
                    'table_count': table_count,
                    'server_time': server_time.isoformat() if server_time else None,
                    'connection_time_ms': connection_time
                },
                'timestamp': datetime.now().isoformat()
            })
        
    except Error as e:
        return jsonify({
            'status': 'error',
            'message': f'RDS连接失败: {str(e)}',
            'error_code': e.errno if hasattr(e, 'errno') else None,
            'config': {
                'host': config['host'],
                'port': config['port'],
                'user': config['user'],
                'database': config['database']
            },
            'timestamp': datetime.now().isoformat()
        }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'未知错误: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@debug_bp.route('/rds-info')
def rds_info():
    """获取RDS配置信息"""
    config = get_rds_config()
    
    return jsonify({
        'status': 'success',
        'rds_config': {
            'host': config['host'] if config else 'N/A',
            'port': config['port'] if config else 'N/A',
            'user': config['user'] if config else 'N/A',
            'database': config['database'] if config else 'N/A',
            'password_set': bool(config and config['password']) if config else False
        },
        'environment': {
            'DATABASE_URL_set': bool(os.environ.get('DATABASE_URL')),
            'RDS_HOST': os.environ.get('RDS_HOST', 'N/A'),
            'RDS_PORT': os.environ.get('RDS_PORT', 'N/A')
        },
        'timestamp': datetime.now().isoformat()
    })

@debug_bp.route('/tables')
def list_tables():
    """列出数据库中的所有表"""
    config = get_rds_config()
    if not config:
        return jsonify({
            'status': 'error',
            'message': '无法解析数据库配置'
        }), 500
    
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        table_info = []
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            
            cursor.execute(f"SHOW CREATE TABLE {table}")
            create_info = cursor.fetchone()
            
            table_info.append({
                'name': table,
                'row_count': row_count,
                'created': create_info[1][:100] + '...' if create_info and len(create_info[1]) > 100 else create_info[1] if create_info else 'N/A'
            })
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'status': 'success',
            'message': f'找到 {len(tables)} 个数据表',
            'tables': table_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Error as e:
        return jsonify({
            'status': 'error',
            'message': f'查询表信息失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# 注册蓝图到Flask应用的函数
def register_debug_blueprint(app):
    """注册调试蓝图到Flask应用"""
    app.register_blueprint(debug_bp)
    return debug_bp