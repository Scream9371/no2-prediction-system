import requests
from datetime import datetime, timedelta
from utils.auth import generate_jwt_token, get_heweather_config

class HeWeatherClient:
    def __init__(self):
        self.config = get_heweather_config()

    def generate_jwt_token(self):
        """生成JWT令牌"""
        return generate_jwt_token()

    def get_city_id(self, city_name):
        """获取城市ID"""
        token = self.generate_jwt_token()
        url = f"https://{self.config['api_host']}/geo/v2/city/lookup?location={city_name}"
        headers = {"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "200" and data.get("location"):
                return data["location"][0]["id"]
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取城市ID失败: {str(e)}")
            return None

    def get_historical_air_quality(self, city_id, date):
        """获取历史空气质量数据"""
        token = self.generate_jwt_token()
        url = f"https://{self.config['api_host']}/v7/historical/air?location={city_id}&date={date}"
        headers = {"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "200":
                return data
            else:
                print(f"API错误: {data.get('code')} - {data.get('message', 'Unknown error')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取历史空气质量数据失败: {str(e)}")
            return None

    def get_historical_weather(self, city_id, date):
        """获取历史天气数据"""
        token = self.generate_jwt_token()
        url = f"https://{self.config['api_host']}/v7/historical/weather?location={city_id}&date={date}"
        headers = {"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "200":
                return data
            else:
                print(f"API错误: {data.get('code')} - {data.get('message', 'Unknown error')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取历史天气数据失败: {str(e)}")
            return None

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
            air_data = self.get_historical_air_quality(city_id, date_str)
            
            # 获取天气数据
            weather_data = self.get_historical_weather(city_id, date_str)
            
            if air_data and weather_data:
                results.append({
                    "date": date_str,
                    "city_id": city_id,
                    "city_name": city_name,
                    "air_data": air_data,
                    "weather_data": weather_data
                })
            
            # 添加延迟避免API限制
            time.sleep(0.1)
        
        return results

    # 保持向后兼容性
    def get_air_quality(self, city_id):
        """获取当前空气质量数据（向后兼容）"""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.get_historical_air_quality(city_id, date_str)
