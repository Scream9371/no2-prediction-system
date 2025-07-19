import os
from datetime import datetime, timedelta
import time
import requests
from utils.auth import get_heweather_config, generate_jwt_token


class HeWeatherClient:
    """和风天气API客户端"""

    def __init__(self):
        """初始化客户端"""
        config = get_heweather_config()
        self.api_host = f"https://{config['api_host']}"  # 添加https://

    def _make_request(self, endpoint: str, params: dict) -> dict:
        """发送API请求的通用方法"""
        url = f"{self.api_host}{endpoint}"
        headers = {"Authorization": f"Bearer {generate_jwt_token()}"}
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # 会抛出HTTPError异常
            data = response.json()

            # 检查API响应状态码
            if str(data.get("code")) != "200":
                print(f"API返回错误: {data.get('code')} - {data.get('fxLink', '')}")
                return None

            return data
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {str(e)}")
            return None

    def get_city_id(self, city_name: str) -> str:
        """获取城市ID"""
        data = self._make_request(
            "/geo/v2/city/lookup",
            {"location": city_name},
        )
        if data and data.get("location"):
            return data["location"][0].get("id")
        return None

    def _is_valid_historical_date(self, date_str: str) -> bool:
        """
        验证历史数据请求的日期是否有效（过去10天内）
        """
        try:
            request_date = datetime.strptime(date_str, "%Y%m%d")
            now = datetime.now()
            days_diff = (now - request_date).days
            return 1 <= days_diff <= 10  # 不包括今天，最多10天前
        except ValueError:
            return False

    def get_historical_weather(self, city_id: str, date: str) -> dict:
        """获取历史天气数据"""
        if not self._is_valid_historical_date(date):
            print(f"无效的历史日期: {date}，只能查询过去1-10天的数据")
            return None

        data = self._make_request(
            "/v7/historical/weather",  # 修正为正确的endpoint
            {"location": city_id, "date": date},
        )
        return data

    def get_historical_air(self, city_id: str, date: str) -> dict:
        """获取历史空气质量数据"""
        if not self._is_valid_historical_date(date):
            print(f"无效的历史日期: {date}，只能查询过去1-10天的数据")
            return None

        data = self._make_request(
            "/v7/historical/air",  # 修正为正确的endpoint
            {"location": city_id, "date": date},
        )
        return data

    def get_city_data_for_date_range(self, city_name, days=10):
        """获取城市指定天数范围内的数据"""
        city_id = self.get_city_id(city_name)
        if not city_id:
            print(f"无法获取城市 {city_name} 的ID")
            return []

        results = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")

            # 获取空气质量数据
            air_data = self.get_historical_air(city_id, date_str)

            # 获取天气数据
            weather_data = self.get_historical_weather(city_id, date_str)

            if air_data and weather_data:
                results.append(
                    {
                        "date": date_str,
                        "city_id": city_id,
                        "city_name": city_name,
                        "air_data": air_data,
                        "weather_data": weather_data,
                    }
                )

            # 添加延迟避免API限制
            time.sleep(0.1)

        return results

