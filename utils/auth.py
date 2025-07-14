"""
和风天气API认证工具
提供统一的私钥获取和JWT生成功能
"""
import os
import jwt
import time
from dotenv import load_dotenv

# 确保加载环境变量
load_dotenv()

def load_private_key():
    """
    加载Ed25519私钥，处理不同环境下的路径问题
    
    Returns:
        str: 私钥内容，如果失败返回None
    """
    # 从环境变量获取路径
    key_file = os.getenv("HF_PRIVATE_KEY_FILE")
    
    # 处理 Git Bash/MSYS2 环境下的路径问题
    if os.getenv('MSYSTEM') and key_file and not os.path.exists(key_file):
        key_file = "ed25519-private.pem"
    elif not key_file:
        key_file = "ed25519-private.pem"
    
    # 如果还是相对路径且不存在，尝试从项目根目录读取
    if not os.path.isabs(key_file) and not os.path.exists(key_file):
        # 获取项目根目录（假设该文件在utils子目录中）
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        key_file = os.path.join(project_root, "ed25519-private.pem")
    
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            raise FileNotFoundError(f"读取私钥文件失败: {key_file}, 错误: {str(e)}")
    else:
        raise FileNotFoundError(f"私钥文件未找到: {key_file}")

def get_heweather_config():
    """
    获取和风天气API配置
    
    Returns:
        dict: 包含所有必要配置的字典
    """
    return {
        'api_host': os.getenv("HF_API_HOST"),
        'private_key': load_private_key(),
        'project_id': os.getenv("HF_PROJECT_ID"),
        'key_id': os.getenv("HF_KEY_ID")
    }

def generate_jwt_token():
    """
    生成和风天气API的JWT令牌
    
    Returns:
        str: JWT令牌
    """
    config = get_heweather_config()
    
    # 验证必要参数
    required_fields = ['api_host', 'private_key', 'project_id', 'key_id']
    for field in required_fields:
        if not config.get(field):
            raise ValueError(f"缺少必要的配置参数: {field}")
    
    # 生成JWT
    token = jwt.encode(
        payload={
            "iat": int(time.time()) - 30,
            "exp": int(time.time()) + 900,
            "sub": config['project_id'],
        },
        key=config['private_key'],
        algorithm="EdDSA",
        headers={"alg": "EdDSA", "kid": config['key_id']},
    )
    
    return token