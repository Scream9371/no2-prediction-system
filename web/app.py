import os

from flask import Flask

from config.cities import init_city_mappings
from web.routes.api_routes import api_bp
from web.routes.main_routes import main_bp

# 设置正确的template和static目录路径
web_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(web_dir, 'templates')
static_dir = os.path.join(web_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='/static')
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

# 初始化城市映射（使用文件系统缓存，避免重复初始化）
if init_city_mappings():
    print("城市映射初始化成功")
else:
    print("警告：城市映射初始化失败，可能影响应用功能")

if __name__ == "__main__":
    app.run(debug=True)
