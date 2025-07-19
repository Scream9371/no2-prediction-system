"""
数据采集模块

此模块负责从和风天气API采集大湾区11个城市的天气和空气质量数据，
并将数据解析后保存到MySQL数据库中。专注于历史数据的采集和存储。

主要功能：
- 采集11个大湾区城市的NO2浓度、温度、湿度、风速、风向、气压数据
- 支持批量采集指定天数的历史数据
- 数据按时间升序存储，确保时间序列正确
- 具备错误处理和API限流保护机制

典型用法：
    # 采集历史数据
    collect_historical_data(days=10)

Author: NO2预测系统开发团队
Date: 2025-07-19
Version: 2.0
"""

from api.heweather.client import HeWeatherClient
from api.heweather.data_parser import parse_combined_data
from database.crud import create_no2_record
from database.session import get_db
from config.settings import settings
from datetime import datetime, timedelta
import time

# 大湾区11个城市
CITY_LIST = [
    "广州",
    "深圳",
    "珠海",
    "佛山",
    "惠州",
    "东莞",
    "中山",
    "江门",
    "肇庆",
    "香港",
    "澳门",
]




def collect_historical_data(days=10):
    """
    收集所有城市指定天数的历史天气和空气质量数据
    
    按时间顺序从最早日期开始收集数据，确保数据库中的时间序列正确排列。
    每个城市每天收集24小时的完整数据。
    
    Args:
        days (int): 需要收集的历史天数，默认为10天
        
    Returns:
        None: 数据直接保存到数据库，无返回值
        
    Raises:
        Exception: 当数据采集过程中发生错误时抛出异常
        
    Note:
        - 采集范围：从今天往前推{days}天到昨天的数据
        - 数据按时间升序保存（从最早到最晚）
        - 总计采集：11个城市 × {days}天 × 24小时的数据
        - 请求间有0.5秒延迟以避免API限流
        - 无法获取城市ID或数据解析失败的会跳过并记录
    """
    client = HeWeatherClient()
    db_gen = get_db()
    db = next(db_gen)

    try:
        for city in CITY_LIST:
            print(f"正在收集 {city} 过去{days}天的历史数据...")

            city_id = client.get_city_id(city)
            if not city_id:
                print(f"无法获取城市 {city} 的ID，跳过")
                continue

            # 收集过去指定天数的数据（从最早日期开始，按时间顺序）
            for i in range(days, 0, -1):  # 从10天前开始，到昨天结束，按时间顺序
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime("%Y%m%d")

                print(f"  收集 {city} {date_str} 的数据...")

                # 获取历史数据
                air_data = client.get_historical_air(city_id, date_str)
                weather_data = client.get_historical_weather(city_id, date_str)

                if air_data and weather_data:
                    parsed_data_list = parse_combined_data(
                        air_data, weather_data, city_id, city, date_str
                    )

                    if parsed_data_list:
                        # 保存所有小时的数据
                        saved_count = 0
                        for hourly_data in parsed_data_list:
                            try:
                                create_no2_record(db, hourly_data, city)
                                saved_count += 1
                            except Exception as e:
                                print(f"    保存 {city} {date_str} 一小时数据失败: {str(e)}")
                        print(f"    成功收集 {city} {date_str} 的 {saved_count} 小时数据")
                    else:
                        print(f"    解析 {city} {date_str} 的数据失败")
                else:
                    print(f"    获取 {city} {date_str} 的数据失败")

                # 添加延迟避免API限制
                time.sleep(0.5)

            print(f"完成收集 {city} 的历史数据")

    except Exception as e:
        print(f"收集历史数据过程中发生错误: {str(e)}")
    finally:
        db.close()


def collect_and_store():
    """
    默认数据收集函数，收集历史数据
    
    此函数固定收集过去10天的历史数据，适用于cron定时任务或脚本调用。
    系统专注于历史数据采集，确保数据完整性和预测准确性。
    
    Args:
        无参数
        
    Returns:
        None: 无返回值，操作结果通过控制台输出
        
    Note:
        - 固定调用collect_historical_data收集过去10天数据
        - 保持与原接口的兼容性
        - 适合用于初始化数据库或完整数据更新
        - 总计采集约2640条记录（11城市×10天×24小时）
    """
    print("开始收集历史数据...")
    collect_historical_data(days=10)
    print("历史数据收集完成")
