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

# 初始化城市映射（只在Flask reloader子进程或非debug模式中执行）
# WERKZEUG_RUN_MAIN='true' 表示在reloader子进程中
# 如果环境中没有该变量，表示非debug模式直接运行
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or 'WERKZEUG_RUN_MAIN' not in os.environ:
    print("正在初始化城市映射...")
    if init_city_mappings():
        print("城市映射初始化成功")
    else:
        print("警告：城市映射初始化失败，可能影响应用功能")

if __name__ == "__main__":
    app.run(debug=True)
