def parse_air_quality(data):
    if data.get("code") != "200":
        return None
    now = data.get("now", {})
    return {
        "no2": float(now.get("no2", 0)),
        "pm25": float(now.get("pm2p5", 0)),
        "temperature": float(now.get("temp", 0)),
        "humidity": float(now.get("humidity", 0)),
        "wind_speed": float(now.get("windSpeed", 0)),
        "weather": now.get("category", ""),
    }
