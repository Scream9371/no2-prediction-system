import os
import requests
from dotenv import load_dotenv 

# 从环境变量获取后端基础URL，默认值为本地开发地址
BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")

def fetch_no2_data(city_id):
    url = f"{BASE_URL}/api/no2/{city_id}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return []
