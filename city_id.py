import os
import time

import jwt
import requests
from dotenv import load_dotenv

# 加载环境变量，用于记录ID以及密钥信息
load_dotenv()

# 从环境变量获取配置
API_HOST = os.getenv("HF_API_HOST")

# WSL环境下python-dotenv可能无法正确处理多行私钥，使用备用方案
def get_private_key():
    """获取正确格式的私钥"""
    key = os.getenv("HF_PRIVATE_KEY")
    if not key or len(key) < 100:  # 如果私钥不完整，使用备用方案
        # 硬编码私钥以解决WSL兼容性问题
        return """-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIFFIzraECKVymQXx9CLwVgBbypHk+SKwM4DGwPWb6vRk
-----END PRIVATE KEY-----"""
    else:
        # 正常处理换行符
        return key.replace("\\r\\n", "\n").replace("\\n", "\n")

PRIVATE_KEY = get_private_key()
PROJECT_ID = os.getenv("HF_PROJECT_ID")
KEY_ID = os.getenv("HF_KEY_ID")


def generate_jwt_token():
    """
    生成JWT令牌
    """
    # 生成JWT
    token = jwt.encode(
        payload={
            "iat": int(time.time()) - 30,
            "exp": int(time.time()) + 900,
            "sub": PROJECT_ID,
        },
        key=PRIVATE_KEY,
        algorithm="EdDSA",
        headers={"alg": "EdDSA", "kid": KEY_ID},
    )

    # 调试输出
    # print("生成的JWT:", token)
    return token


def get_city_id(city_name):
    """
    获取空气质量数据
    :param lat: 纬度
    :param lng: 经度
    """
    # 生成认证令牌
    token = generate_jwt_token()

    # 构造API URL（按照文档格式）
    url = f"https://{API_HOST}/geo/v2/city/lookup?location={city_name}"

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
