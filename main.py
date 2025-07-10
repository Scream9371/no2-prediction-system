import json
import os
import time

import jwt
import requests
from dotenv import load_dotenv

# 加载环境变量，用于记录ID以及密钥信息
load_dotenv()

# 从环境变量获取配置
API_HOST = os.getenv("HF_API_HOST")
PRIVATE_KEY = os.getenv("HF_PRIVATE_KEY")
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
        key=PROJECT_ID,
        algorithm="EdDSA",
        headers={"alg": "EdDSA", "kid": KEY_ID},
    )

    # 调试输出
    print("生成的JWT:", token)
    return token


def get_air_quality(city_id, date):
    """
    获取空气质量数据
    """
    # 生成认证令牌
    token = generate_jwt_token()

    # API URL
    url = f"https://{API_HOST}/v7/historical/air?location={city_id}&date={date}"

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
    city_id, date = 101281301, 20250705

    # 获取数据
    result = get_air_quality(city_id, date)

    if result:
        print("空气质量数据:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("获取数据失败")
