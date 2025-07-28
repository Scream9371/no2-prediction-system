"""
maoyuxuan专用PythonAnywhere WSGI配置文件
用于在maoyuxuan.pythonanywhere.com部署NO2预测系统
"""
import sys
import os

# maoyuxuan用户的项目路径
project_home = '/home/maoyuxuan/no2-prediction-system'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 设置环境变量
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'maoyuxuan-no2-prediction-2025'

# MySQL数据库配置（请将YOUR_MYSQL_PASSWORD替换为实际密码）
os.environ['DATABASE_URL'] = 'mysql://maoyuxuan:YOUR_MYSQL_PASSWORD@maoyuxuan.mysql.pythonanywhere-services.com/maoyuxuan$no2prediction'

# 和风天气API配置（如果您有API密钥，请取消注释并填入）
# os.environ['HF_API_HOST'] = 'your_api_host'
# os.environ['HF_PROJECT_ID'] = 'your_project_id' 
# os.environ['HF_KEY_ID'] = 'your_credential_id'

# 导入Flask应用
try:
    from app_deploy import app as application
    print("✓ Flask应用加载成功 - maoyuxuan")
except ImportError as e:
    print(f"✗ Flask应用加载失败: {e}")
    # 创建一个简单的WSGI应用作为后备
    def application(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        return [f'''
        <html>
            <head><title>NO2 Prediction System - maoyuxuan</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h1>🌍 NO2预测系统</h1>
                <p><strong>状态</strong>: 系统正在初始化中...</p>
                <p><strong>部署地址</strong>: maoyuxuan.pythonanywhere.com</p>
                <p><strong>错误信息</strong>: {str(e)}</p>
                <hr>
                <p>如果您看到此页面，说明Web应用已成功配置，但Flask应用模块需要进一步设置。</p>
                <p>请检查项目文件是否完整上传，并确认依赖包已正确安装。</p>
            </body>
        </html>
        '''.encode('utf-8')]

# 确保应用可以被WSGI服务器调用
if __name__ == "__main__":
    # 本地测试
    if hasattr(application, 'run'):
        application.run(debug=False, host='0.0.0.0', port=8000)
    else:
        print("WSGI application ready for maoyuxuan.pythonanywhere.com")