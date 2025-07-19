from datetime import datetime, timedelta
import pytest
from api.heweather.client import HeWeatherClient


@pytest.fixture
def client():
    return HeWeatherClient()


def test_client_initialization(client):
    """测试客户端初始化"""
    assert client.api_host is not None


def test_get_city_info(client):  # 更正方法名
    """测试获取城市信息"""
    city_name = "广州"
    city_info = client.get_city_info(city_name)

    assert city_info is not None
    assert "id" in city_info
    assert "lat" in city_info
    assert "lon" in city_info


def test_get_historical_weather(client):
    """测试获取历史天气数据"""
    city_id = "101280101"  # 广州
    # 获取10天前的日期
    test_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
    data = client.get_historical_weather(city_id, test_date)

    assert data is not None
    assert "code" in data
    assert data["code"] == "200"


def test_get_historical_air(client):
    """测试获取历史空气质量数据"""
    city_id = "101280101"  # 广州
    # 获取10天前的日期
    test_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
    data = client.get_historical_air(city_id, test_date)

    assert data is not None
    assert "code" in data
    assert data["code"] == "200"
