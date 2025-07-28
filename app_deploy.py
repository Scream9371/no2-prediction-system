"""
免费托管平台部署启动文件
适配Railway、Render等平台的部署需求
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault('FLASK_ENV', 'production')

def create_app():
    """创建Flask应用实例"""
    try:
        # 导入主应用
        from web.app import app
        
        # 生产环境配置
        app.config.update(
            DEBUG=False,
            TESTING=False,
            SECRET_KEY=os.environ.get('SECRET_KEY', 'railway-deploy-secret-key-2025')
        )
        
        # 初始化数据库（如果需要）
        try:
            from database.session import init_database
            init_database()
            print("数据库初始化成功")
        except Exception as db_error:
            print(f"数据库初始化失败: {db_error}")
            print("将使用轻量级模式运行")
        
        return app
        
    except ImportError as e:
        print(f"导入错误: {e}")
        # 创建一个简单的Flask应用作为回退
        from flask import Flask
        fallback_app = Flask(__name__)
        
        @fallback_app.route('/')
        def hello():
            return '''
            <h1>NO2 预测系统</h1>
            <p>系统正在初始化中，请稍后访问...</p>
            <p>如果问题持续存在，请联系管理员。</p>
            '''
        
        return fallback_app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)