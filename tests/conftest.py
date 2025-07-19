import pytest
import os
from dotenv import load_dotenv


@pytest.fixture(autouse=True)
def load_env():
    """自动加载环境变量"""
    load_dotenv()

    # 验证必要的环境变量
    required_vars = [
        "HF_API_HOST",
        "HF_PRIVATE_KEY_FILE",
        "HF_PROJECT_ID",
        "HF_KEY_ID",
        "DATABASE_URL",
    ]

    for var in required_vars:
        assert os.getenv(var) is not None, f"缺少环境变量: {var}"
