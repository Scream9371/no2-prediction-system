"""
PythonAnywhere部署设置脚本
适用于PythonAnywhere免费账户
"""
import os
import sys

def create_wsgi_file():
    """创建WSGI配置文件"""
    wsgi_content = '''
import sys
import os

# 项目路径（需要根据实际情况修改）
project_home = '/home/yourusername/no2-prediction-system'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 设置环境变量
os.environ['DATABASE_URL'] = 'sqlite:///./no2_prediction.db'
os.environ['FLASK_ENV'] = 'production'

from app_deploy import app as application

if __name__ == "__main__":
    application.run()
'''
    
    with open('wsgi.py', 'w', encoding='utf-8') as f:
        f.write(wsgi_content)
    
    print("已创建 wsgi.py 文件")
    print("请根据您的PythonAnywhere用户名修改路径")

def create_requirements_simple():
    """创建简化的requirements文件"""
    # 移除可能在PythonAnywhere上有问题的包
    with open('requirements.txt', 'r') as f:
        lines = f.readlines()
    
    # 过滤掉可能有问题的包
    filtered_lines = []
    skip_packages = ['torch==', 'scipy==']  # 这些包太大，可能超出免费限制
    
    for line in lines:
        should_skip = any(skip in line for skip in skip_packages)
        if not should_skip:
            filtered_lines.append(line)
    
    with open('requirements_pythonanywhere.txt', 'w') as f:
        f.writelines(filtered_lines)
    
    print("已创建 requirements_pythonanywhere.txt")

if __name__ == "__main__":
    create_wsgi_file()
    create_requirements_simple()
    print("\nPythonAnywhere部署文件已创建完成！")
    print("上传步骤：")
    print("1. 注册 pythonanywhere.com 免费账户")
    print("2. 上传项目文件到 ~/no2-prediction-system/")
    print("3. 在Web面板中配置WSGI文件路径")
    print("4. 安装依赖：pip3.8 install --user -r requirements_pythonanywhere.txt")