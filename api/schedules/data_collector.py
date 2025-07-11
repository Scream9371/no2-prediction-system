from api.heweather.client import HeWeatherClient
from api.heweather.data_parser import parse_combined_data
from database.crud import create_no2_record
from database.session import get_db
from config.settings import settings
from datetime import datetime, timedelta
import time

# 大湾区11个城市
CITY_LIST = [
    "广州", "深圳", "珠海", "佛山", "惠州", 
    "东莞", "中山", "江门", "肇庆", "香港", "澳门"
]

def collect_current_data():
    """收集当前数据（向后兼容）"""
    client = HeWeatherClient()
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        for city in CITY_LIST:
            print(f"正在收集 {city} 的当前数据...")
            
            city_id = client.get_city_id(city)
            if not city_id:
                print(f"无法获取城市 {city} 的ID，跳过")
                continue
            
            # 获取当前数据
            current_date = datetime.now().strftime("%Y%m%d")
            air_data = client.get_historical_air_quality(city_id, current_date)
            weather_data = client.get_historical_weather(city_id, current_date)
            
            if air_data and weather_data:
                parsed_data = parse_combined_data(
                    air_data, weather_data, city_id, city, current_date
                )
                
                if parsed_data:
                    create_no2_record(db, parsed_data)
                    print(f"成功收集 {city} 的数据")
                else:
                    print(f"解析 {city} 的数据失败")
            else:
                print(f"获取 {city} 的数据失败")
            
            # 添加延迟避免API限制
            time.sleep(1)
            
    except Exception as e:
        print(f"收集数据过程中发生错误: {str(e)}")
    finally:
        db.close()

def collect_historical_data(days=10):
    """收集历史数据（距今指定天数）"""
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
            
            # 收集过去指定天数的数据
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime("%Y%m%d")
                
                print(f"  收集 {city} {date_str} 的数据...")
                
                # 获取历史数据
                air_data = client.get_historical_air_quality(city_id, date_str)
                weather_data = client.get_historical_weather(city_id, date_str)
                
                if air_data and weather_data:
                    parsed_data = parse_combined_data(
                        air_data, weather_data, city_id, city, date_str
                    )
                    
                    if parsed_data:
                        create_no2_record(db, parsed_data)
                        print(f"    成功收集 {city} {date_str} 的数据")
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
    """默认数据收集函数（收集当前数据，保持向后兼容）"""
    print("开始收集当前数据...")
    collect_current_data()
    print("当前数据收集完成")

def collect_and_store_historical():
    """收集历史数据的主函数"""
    print("开始收集历史数据...")
    collect_historical_data(days=10)
    print("历史数据收集完成")

if __name__ == "__main__":
    # 可以选择收集当前数据或历史数据
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "historical":
        collect_and_store_historical()
    else:
        collect_and_store()
