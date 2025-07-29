"""
调度配置模块

定义每日数据更新任务的配置参数和策略
"""

from datetime import time
from typing import Dict, Any, List
import os

class ScheduleConfig:
    """调度配置类"""
    
    # 基本调度配置
    DAILY_UPDATE_TIME = time(2, 0)  # 每日02:00执行
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY_MINUTES = 60  # 重试延迟（分钟）
    
    # API调用配置
    API_REQUEST_DELAY = 0.5  # API请求间隔（秒）
    API_TIMEOUT = 30  # API超时时间（秒）
    
    # 数据质量阈值
    DATA_QUALITY_THRESHOLDS = {
        'no2_concentration': {
            'min': 0,
            'max': 500,
            'unit': 'μg/m³'
        },
        'temperature': {
            'min': -30,
            'max': 50,
            'unit': '°C'
        },
        'humidity': {
            'min': 0,
            'max': 100,
            'unit': '%'
        },
        'wind_speed': {
            'min': 0,
            'max': 200,
            'unit': 'km/h'
        },
        'wind_direction': {
            'min': 0,
            'max': 360,
            'unit': '°'
        },
        'pressure': {
            'min': 800,
            'max': 1200,
            'unit': 'hPa'
        }
    }
    
    # 监控配置
    MONITORING = {
        'max_execution_time_minutes': 15,  # 最大执行时间
        'min_success_rate': 0.95,  # 最小成功率
        'alert_on_consecutive_failures': 3,  # 连续失败告警阈值
    }
    
    # 大湾区11个城市列表
    CITIES = [
        "广州", "深圳", "珠海", "佛山", "惠州",
        "东莞", "中山", "江门", "肇庆", "香港", "澳门"
    ]
    
    # 日志配置
    LOG_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_prefix': 'daily_updater',
        'max_log_files': 30,  # 保留30天的日志
    }
    
    # 通知配置
    NOTIFICATION = {
        'enabled': False,  # 是否启用邮件通知
        'smtp_server': os.getenv('SMTP_SERVER', ''),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'email_user': os.getenv('EMAIL_USER', ''),
        'email_password': os.getenv('EMAIL_PASSWORD', ''),
        'admin_emails': os.getenv('ADMIN_EMAILS', '').split(',') if os.getenv('ADMIN_EMAILS') else [],
        'send_on_failure': True,
        'send_daily_report': False,
    }
    
    @classmethod
    def get_cron_expression(cls) -> str:
        """获取crontab表达式"""
        return f"{cls.DAILY_UPDATE_TIME.minute} {cls.DAILY_UPDATE_TIME.hour} * * *"
    
    @classmethod
    def validate_data_value(cls, field_name: str, value: float) -> bool:
        """验证数据值是否在合理范围内"""
        if field_name not in cls.DATA_QUALITY_THRESHOLDS:
            return True
        
        threshold = cls.DATA_QUALITY_THRESHOLDS[field_name]
        return threshold['min'] <= value <= threshold['max']
    
    @classmethod
    def get_log_file_path(cls) -> str:
        """获取日志文件路径"""
        from datetime import datetime
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        today = datetime.now().strftime('%Y%m%d')
        return os.path.join(log_dir, f"{cls.LOG_CONFIG['file_prefix']}_{today}.log")

# 导出配置实例
schedule_config = ScheduleConfig()