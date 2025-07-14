from datetime import datetime

def parse_air_quality(data):
    """解析当前空气质量数据（向后兼容）"""
    if data.get("code") != "200":
        return None
    
    air_hourly = data.get("airHourly", [])
    if not air_hourly:
        return None
    
    # 取最新的一个小时数据作为当前数据
    latest = air_hourly[-1]
    return {
        "no2": float(latest.get("no2", 0)),
        "pm25": float(latest.get("pm2p5", 0)),
        "aqi": int(latest.get("aqi", 0)),
        "category": latest.get("category", ""),
        "primary": latest.get("primary", ""),
        "so2": float(latest.get("so2", 0)),
        "co": float(latest.get("co", 0)),
        "o3": float(latest.get("o3", 0)),
        "pm10": float(latest.get("pm10", 0)),
    }

def parse_historical_air_quality(data):
    """解析历史空气质量数据"""
    if data.get("code") != "200":
        return None
    
    air_hourly = data.get("airHourly", [])
    if not air_hourly:
        return None
    
    # 取当天的平均值
    total_records = len(air_hourly)
    if total_records == 0:
        return None
    
    # 计算平均值
    no2_sum = sum(float(record.get("no2", 0)) for record in air_hourly)
    pm25_sum = sum(float(record.get("pm2p5", 0)) for record in air_hourly)
    pm10_sum = sum(float(record.get("pm10", 0)) for record in air_hourly)
    so2_sum = sum(float(record.get("so2", 0)) for record in air_hourly)
    co_sum = sum(float(record.get("co", 0)) for record in air_hourly)
    o3_sum = sum(float(record.get("o3", 0)) for record in air_hourly)
    
    return {
        "no2": round(no2_sum / total_records, 2),
        "pm25": round(pm25_sum / total_records, 2),
        "pm10": round(pm10_sum / total_records, 2),
        "so2": round(so2_sum / total_records, 2),
        "co": round(co_sum / total_records, 2),
        "o3": round(o3_sum / total_records, 2),
        "aqi": int(air_hourly[0].get("aqi", 0)),  # 使用第一个小时的AQI
        "primary": air_hourly[0].get("primary", ""),
        "category": air_hourly[0].get("category", ""),
    }

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

def parse_combined_data(air_data, weather_data, city_id, city_name, date):
    """合并解析空气质量和天气数据"""
    air_parsed = parse_historical_air_quality(air_data)
    weather_parsed = parse_historical_weather(weather_data)
    
    if not air_parsed or not weather_parsed:
        return None
    
    # 合并数据
    combined = {
        "city_id": city_id,
        "city_name": city_name,
        "date": date,
        "datetime": datetime.strptime(date, "%Y%m%d"),
        **air_parsed,
        **weather_parsed,
    }
    
    return combined
