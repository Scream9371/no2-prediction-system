from flask import Flask
from web.routes.main_routes import main_bp
from web.routes.api_routes import api_bp
from config.cities import init_city_mappings

app = Flask(__name__)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

# 初始化城市映射
print("正在初始化城市映射...")
if init_city_mappings():
    print("城市映射初始化成功")
else:
    print("警告：城市映射初始化失败，可能影响应用功能")

if __name__ == "__main__":
    app.run(debug=True)
