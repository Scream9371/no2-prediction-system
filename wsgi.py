
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
