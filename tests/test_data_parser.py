import pytest
from datetime import datetime
from api.heweather.data_parser import parse_combined_data


@pytest.mark.parser  # 添加标记便于管理测试用例
def test_parse_combined_data():
    """测试数据解析功能"""
    # 模拟API返回的数据
    air_data = {
        "code": "200",
        "hourly": [{"pubTime": "2024-03-01T12:00:00+08:00", "no2": "45"}],
    }

    weather_data = {
        "code": "200",
        "hourly": [
            {
                "fxTime": "2024-03-01T12:00:00+08:00",
                "temp": "25",
                "humidity": "80",
                "wind360": "180",
                "windSpeed": "15",
                "pressure": "1013",
            }
        ],
    }

    result = parse_combined_data(
        air_data, weather_data, "101280101", "广州", "20240301"
    )

    assert result is not None
    assert isinstance(result["observation_time"], datetime)
    assert isinstance(result["no2_concentration"], float)
    assert isinstance(result["temperature"], float)
