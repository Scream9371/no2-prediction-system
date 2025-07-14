import requests
from utils.auth import generate_jwt_token, get_heweather_config


def get_city_id(city_name):
    """
    获取城市ID
    :param city_name: 城市名称
    """
    # 生成认证令牌
    token = generate_jwt_token()
    config = get_heweather_config()

    # 构造API URL（按照文档格式）
    url = f"https://{config['api_host']}/geo/v2/city/lookup?location={city_name}"

    # 设置请求头（按照文档格式）
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


# 使用示例
if __name__ == "__main__":
    # 测试坐标
    cities = [
        "广州",
        "深圳",
        "佛山",
        "东莞",
        "中山",
        "珠海",
        "江门",
        "肇庆",
        "惠州",
        "香港",
        "澳门",
    ]

    # 获取数据
    for city in cities:
        js = get_city_id(city)
        # print(js)

        loc = js["location"][0]
        result = f"{loc['name']}({loc['id']})"

        # 处理结果
        if result:
            print(result)
        else:
            print("获取数据失败")
