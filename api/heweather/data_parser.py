from datetime import datetime
from typing import Dict, Any, Optional, List

def parse_historical_data(
    air_data: Dict[str, Any],
    weather_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    解析历史天气和空气质量数据
    
    Args:
        air_data: 空气质量数据
        weather_data: 天气数据
        
    Returns:
        解析后的数据字典，包含:
        - observation_time: datetime (ISO8601:2004格式)
        - no2_concentration: float (μg/m³)
        - temperature: float (摄氏度)
        - humidity: float (百分比)
        - wind_speed: float (公里/小时)  
        - wind_direction: float (360角度)
        - pressure: float (百帕)
    """
    try:
        if not air_data or not weather_data:
            return None
            
        # 获取当天平均值
        air_hourly = air_data.get('hourly', [])
        weather_hourly = weather_data.get('weatherHourly', [])
        
        if not air_hourly or not weather_hourly:
            return None
            
        # 计算平均值
        no2_sum = sum(float(h.get('no2', 0)) for h in air_hourly)
        temp_sum = sum(float(h.get('temp', 0)) for h in weather_hourly)
        humidity_sum = sum(float(h.get('humidity', 0)) for h in weather_hourly)
        wind_speed_sum = sum(float(h.get('windSpeed', 0)) for h in weather_hourly)
        wind_dir_sum = sum(float(h.get('wind360', 0)) for h in weather_hourly)
        pressure_sum = sum(float(h.get('pressure', 0)) for h in weather_hourly)
        
        count = len(weather_hourly)
        
        return {
            'observation_time': datetime.fromisoformat(air_hourly[0]['pubTime'].replace('Z', '+00:00')),
            'no2_concentration': round(no2_sum / count, 2),
            'temperature': round(temp_sum / count, 2),
            'humidity': round(humidity_sum / count, 2),
            'wind_speed': round(wind_speed_sum / count, 2),
            'wind_direction': round(wind_dir_sum / count, 2),
            'pressure': round(pressure_sum / count, 2)
        }
    except (KeyError, ValueError, ZeroDivisionError) as e:
        print(f"数据解析错误: {str(e)}")
        return None

def parse_historical_weather(data):
    """解析历史天气数据"""
    if data.get("code") != "200":
        return None
    
    weather_hourly = data.get("weatherHourly", [])
    if not weather_hourly:
        return None
    
    # 取当天的平均值和统计信息
    total_records = len(weather_hourly)
    if total_records == 0:
        return None
    
    # 计算平均值
    temp_sum = sum(float(record.get("temp", 0)) for record in weather_hourly)
    humidity_sum = sum(float(record.get("humidity", 0)) for record in weather_hourly)
    wind_speed_sum = sum(float(record.get("windSpeed", 0)) for record in weather_hourly)
    pressure_sum = sum(float(record.get("pressure", 0)) for record in weather_hourly)
    
    return {
        "temperature": round(temp_sum / total_records, 2),
        "humidity": round(humidity_sum / total_records, 2),
        "wind_speed": round(wind_speed_sum / total_records, 2),
        "pressure": round(pressure_sum / total_records, 2),
        "weather": weather_hourly[0].get("text", ""),
        "wind_dir": weather_hourly[0].get("windDir", ""),
    }

def parse_combined_data(
    air_data: Dict[str, Any],
    weather_data: Dict[str, Any],
    city_id: str,
    city_name: str,
    date: str
) -> Optional[List[Dict[str, Any]]]:
    """
    解析和组合天气与空气质量数据，返回24小时的完整数据
    
    Returns:
        包含24小时数据的列表，每个元素是一个小时的数据字典
    """
    try:
        if not air_data or not weather_data:
            return None
            
        # 获取完整的小时级数据
        air_hourly_list = air_data.get('airHourly', [])
        weather_hourly_list = weather_data.get('weatherHourly', [])
        
        if not air_hourly_list or not weather_hourly_list:
            print("空气质量或天气数据为空")
            return None
        
        # 确保两个数据源的小时数据长度一致
        min_length = min(len(air_hourly_list), len(weather_hourly_list))
        if min_length == 0:
            print("没有可用的小时级数据")
            return None
        
        result_list = []
        
        # 遍历每个小时的数据
        for i in range(min_length):
            air_hourly = air_hourly_list[i]
            weather_hourly = weather_hourly_list[i]
            
            if not air_hourly or not weather_hourly:
                continue
                
            try:
                hourly_data = {
                    'observation_time': datetime.fromisoformat(air_hourly['pubTime'].replace('Z', '+00:00')),
                    'no2_concentration': float(air_hourly['no2']),
                    'temperature': float(weather_hourly['temp']),
                    'humidity': float(weather_hourly['humidity']),
                    'wind_speed': float(weather_hourly['windSpeed']),
                    'wind_direction': float(weather_hourly['wind360']),
                    'pressure': float(weather_hourly['pressure'])
                }
                result_list.append(hourly_data)
            except (KeyError, ValueError) as e:
                print(f"解析第{i+1}小时数据时出错: {str(e)}")
                continue
        
        return result_list if result_list else None
        
    except (KeyError, ValueError) as e:
        print(f"数据解析错误: {str(e)}")
        return None


def parse_combined_data_single(
    air_data: Dict[str, Any],
    weather_data: Dict[str, Any],
    city_id: str,
    city_name: str,
    date: str
) -> Optional[Dict[str, Any]]:
    """
    解析和组合天气与空气质量数据，只返回第一小时数据（向后兼容）
    """
    hourly_data_list = parse_combined_data(air_data, weather_data, city_id, city_name, date)
    return hourly_data_list[0] if hourly_data_list else None
