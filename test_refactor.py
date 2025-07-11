#!/usr/bin/env python3
"""
测试重构后的API代码
使用前请确保在.env文件中配置了正确的JWT参数：
- HF_API_HOST
- HF_PRIVATE_KEY
- HF_PROJECT_ID
- HF_KEY_ID
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.heweather.client import HeWeatherClient
from api.heweather.data_parser import parse_combined_data
from datetime import datetime, timedelta

def test_jwt_token():
    """测试JWT令牌生成"""
    print("=== 测试JWT令牌生成 ===")
    try:
        client = HeWeatherClient()
        token = client.generate_jwt_token()
        print(f"JWT令牌生成成功: {token[:50]}...")
        return True
    except Exception as e:
        print(f"JWT令牌生成失败: {str(e)}")
        return False

def test_city_id():
    """测试城市ID获取"""
    print("\n=== 测试城市ID获取 ===")
    client = HeWeatherClient()
    test_cities = ["广州", "深圳", "香港", "澳门"]
    
    for city in test_cities:
        try:
            city_id = client.get_city_id(city)
            if city_id:
                print(f"{city}: {city_id}")
            else:
                print(f"{city}: 获取失败")
        except Exception as e:
            print(f"{city}: 错误 - {str(e)}")

def test_historical_data():
    """测试历史数据获取"""
    print("\n=== 测试历史数据获取 ===")
    client = HeWeatherClient()
    
    # 使用广州测试
    city_id = client.get_city_id("广州")
    if not city_id:
        print("无法获取广州的城市ID")
        return
    
    # 测试获取昨天的数据
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y%m%d")
    
    print(f"测试获取广州 {date_str} 的数据...")
    
    # 获取空气质量数据
    air_data = client.get_historical_air_quality(city_id, date_str)
    if air_data:
        print("空气质量数据获取成功")
        print(f"  状态码: {air_data.get('code')}")
        print(f"  数据条数: {len(air_data.get('airHourly', []))}")
    else:
        print("空气质量数据获取失败")
        return
    
    # 获取天气数据
    weather_data = client.get_historical_weather(city_id, date_str)
    if weather_data:
        print("天气数据获取成功")
        print(f"  状态码: {weather_data.get('code')}")
        print(f"  数据条数: {len(weather_data.get('weatherHourly', []))}")
    else:
        print("天气数据获取失败")
        return
    
    # 测试数据解析
    parsed_data = parse_combined_data(air_data, weather_data, city_id, "广州", date_str)
    if parsed_data:
        print("数据解析成功")
        print(f"  NO2浓度: {parsed_data.get('no2')}")
        print(f"  PM2.5浓度: {parsed_data.get('pm25')}")
        print(f"  平均温度: {parsed_data.get('temperature')}")
        print(f"  平均湿度: {parsed_data.get('humidity')}")
    else:
        print("数据解析失败")

def test_city_list():
    """测试大湾区城市列表"""
    print("\n=== 测试大湾区城市列表 ===")
    from api.schedules.data_collector import CITY_LIST
    
    print(f"城市数量: {len(CITY_LIST)}")
    print("城市列表:")
    for i, city in enumerate(CITY_LIST, 1):
        print(f"  {i}. {city}")
    
    # 验证是否包含香港和澳门
    if "香港" in CITY_LIST and "澳门" in CITY_LIST:
        print("✓ 城市列表包含香港和澳门")
    else:
        print("✗ 城市列表缺少香港或澳门")

def main():
    print("开始测试重构后的API代码...")
    
    # 测试JWT令牌
    if not test_jwt_token():
        print("\n请检查.env文件中的JWT配置参数")
        return
    
    # 测试城市ID获取
    test_city_id()
    
    # 测试历史数据获取
    test_historical_data()
    
    # 测试城市列表
    test_city_list()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()