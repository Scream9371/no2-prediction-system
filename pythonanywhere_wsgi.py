"""
PythonAnywhere WSGI配置文件
用于部署NO2预测系统到PythonAnywhere平台
"""
import sys
import os

# 将用户名替换为您的PythonAnywhere用户名
# 例如：如果您的用户名是 'johnsmith'，则修改为：
# USERNAME = 'johnsmith'
USERNAME = 'yourusername'  # <-- 请修改这里

# 项目路径
project_home = f'/home/{USERNAME}/no2-prediction-system'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 设置环境变量
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'pythonanywhere-no2-prediction-2025'

# MySQL数据库配置（PythonAnywhere免费账户格式）
# 格式：mysql://用户名:密码@mysql.server/用户名$数据库名
os.environ['DATABASE_URL'] = f'mysql://{USERNAME}:数据库密码@{USERNAME}.mysql.pythonanywhere-services.com/{USERNAME}$no2prediction'

# 和风天气API配置（如果有的话）
# os.environ['HF_API_HOST'] = 'your_api_host'
# os.environ['HF_PROJECT_ID'] = 'your_project_id'
# os.environ['HF_KEY_ID'] = 'your_credential_id'

# 导入Flask应用
try:
    from app_deploy import app as application
    print("Flask应用加载成功")
except ImportError as e:
    print(f"Flask应用加载失败: {e}")
    # 创建一个简单的WSGI应用作为后备
    def application(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        return [b'<h1>NO2 Prediction System</h1><p>System is initializing...</p>']

# 确保应用可以被WSGI服务器调用
if __name__ == "__main__":
    # 本地测试
    if hasattr(application, 'run'):
        application.run(debug=False)
    else:
        print("WSGI application ready")