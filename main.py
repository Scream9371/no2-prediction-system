import json
import os
import requests
from utils.auth import generate_jwt_token, get_heweather_config


def get_air_quality(city_id, date):
    """
    获取空气质量数据
    """
    # 生成认证令牌
    token = generate_jwt_token()
    config = get_heweather_config()

    # API URL
    url = f"https://{config['api_host']}/v7/historical/air?location={city_id}&date={date}"

    # 请求头
    headers = {"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip"}

    try:
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)

        # 检查HTTP状态码
        response.raise_for_status()

        # 返回JSON数据
        return response.json()
    except requests.exceptions.RequestException as e:
        # 详细错误处理
        if e.response is not None:
            print(f"API错误响应: {e.response.status_code} - {e.response.text}")
        else:
            print(f"网络请求失败: {str(e)}")
        return None


if __name__ == "__main__":
    # 清远
    city_id, date = 101281301, 20250709

    # 获取数据
    result = get_air_quality(city_id, date)

    if result:
        print("空气质量数据:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("获取数据失败")
