import os
import csv
import requests
from datetime import datetime, timedelta
import pandas as pd
from city_id import get_city_id
from utils.auth import generate_jwt_token, get_heweather_config


def get_past_dates(days=10):
    """
    获取过去n天的日期列表（YYYYMMDD格式）

    Args:
        days (int): 需要获取的天数

    Returns:
        list: 日期字符串列表
    """
    dates = []
    today = datetime.now()
    for i in range(1, days + 1):
        date = today - timedelta(days=i)
        dates.append(date.strftime("%Y%m%d"))
    return dates


def process_air_quality_data(data):
    """
    处理空气质量数据，提取所需字段

    Args:
        data (dict): API返回的原始数据

    Returns:
        list: 处理后的数据记录列表
    """
    records = []

    if not data or "code" not in data or data["code"] != "200":
        return records

    for item in data.get("airHourly", []):
        try:
            record = {
                "observation_time": item.get("fxTime", ""),  # ISO8601格式的观测时间
                "no2": item.get("no2", ""),  # NO₂浓度
                "temp": item.get("temp", ""),  # 气温
                "humidity": item.get("humidity", ""),  # 相对湿度
                "wind_speed": item.get("wind_speed", ""),  # 风速
                "wind_dir": item.get("wind_dir", ""),  # 风向
                "pressure": item.get("pressure", ""),  # 大气压
            }
            records.append(record)
        except Exception as e:
            print(f"处理数据记录时出错: {str(e)}")
            continue

    return records


def get_weather_data(city_id, date):
    """
    获取历史天气数据

    Args:
        city_id (str): 城市ID
        date (str): 日期，格式YYYYMMDD

    Returns:
        dict: 包含天气数据的字典
    """
    token = generate_jwt_token()
    config = get_heweather_config()

    url = f"https://{config['api_host']}/v7/historical/weather?location={city_id}&date={date}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取历史天气数据时出错: {str(e)}")
        return None


def get_air_quality(city_id, date):
    """
    获取历史空气质量数据

    Args:
        city_id (str): 城市ID
        date (str): 日期，格式YYYYMMDD

    Returns:
        dict: 包含空气质量数据的字典
    """
    token = generate_jwt_token()
    config = get_heweather_config()

    url = (
        f"https://{config['api_host']}/v7/historical/air?location={city_id}&date={date}"
    )
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == "200":
            return data
        else:
            print(f"API返回错误: {data.get('code')} - {data.get('message')}")
            return None
    except Exception as e:
        print(f"获取历史空气质量数据时出错: {str(e)}")
        return None


def collect_and_save_data(city_info_list):
    """
    采集数据并按城市分别保存到CSV

    Args:
        city_info_list (list): 包含城市信息的列表
    """
    fieldnames = [
        "observation_time",
        "no2",
        "temperature",
        "humidity",
        "wind_speed",
        "wind_direction",
        "pressure",
    ]

    os.makedirs("data", exist_ok=True)
    past_dates = get_past_dates(10)

    for city in city_info_list:
        # 为每个城市创建单独的CSV文件
        csv_file = f"data/{city['name']}_data.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for date in past_dates:
                try:
                    # 获取历史天气数据
                    weather_data = get_weather_data(city["id"], date)
                    if not weather_data or "weatherHourly" not in weather_data:
                        print(f"获取{city['name']} {date}天气数据失败")
                        continue

                    # 获取历史空气质量数据
                    air_data = get_air_quality(city["id"], date)
                    if not air_data or "airHourly" not in air_data:
                        print(f"获取{city['name']} {date}空气质量数据失败")
                        continue

                    # 处理每小时数据
                    weather_hourly = weather_data.get("weatherHourly", [])
                    air_hourly = air_data.get("airHourly", [])

                    for weather, air in zip(weather_hourly, air_hourly):
                        try:
                            row = {
                                "observation_time": weather.get("time", ""),
                                "no2": air.get("no2", ""),
                                "temperature": weather.get("temp", ""),
                                "humidity": weather.get("humidity", ""),
                                "wind_speed": weather.get("windSpeed", ""),
                                "wind_direction": weather.get("wind360", ""),
                                "pressure": weather.get("pressure", ""),
                            }
                            writer.writerow(row)
                        except Exception as e:
                            print(
                                f"处理{city['name']} {date}的单条数据时出错: {str(e)}"
                            )
                            continue

                    print(f"成功采集{city['name']} {date}的数据")

                except Exception as e:
                    print(f"采集{city['name']} {date}数据时出错: {str(e)}")

        print(f"完成{city['name']}数据的采集和保存")


def main():
    """
    主函数：获取数据并保存到CSV
    """
    # 大湾区城市信息
    cities = [
        {"name": "广州", "id": "101280101", "lat": 23.12908, "lon": 113.26436},
        {"name": "深圳", "id": "101280601", "lat": 22.54700, "lon": 114.08594},
        {"name": "珠海", "id": "101280701", "lat": 22.27073, "lon": 113.57668},
        {"name": "佛山", "id": "101280800", "lat": 23.02185, "lon": 113.12192},
        {"name": "惠州", "id": "101280301", "lat": 23.11075, "lon": 114.41679},
        {"name": "东莞", "id": "101281601", "lat": 23.02067, "lon": 113.75179},
        {"name": "中山", "id": "101281701", "lat": 22.51595, "lon": 113.39277},
        {"name": "江门", "id": "101281101", "lat": 22.57865, "lon": 113.08161},
        {"name": "肇庆", "id": "101280901", "lat": 23.04751, "lon": 112.46528},
        {"name": "香港", "id": "101320101", "lat": 22.27832, "lon": 114.17469},
        {"name": "澳门", "id": "101330101", "lat": 22.19875, "lon": 113.54913},
    ]

    collect_and_save_data(cities)


if __name__ == "__main__":
    main()
