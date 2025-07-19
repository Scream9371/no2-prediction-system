import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.schedules.data_collector import collect_and_store

if __name__ == "__main__":
    collect_and_store()
    print("数据采集完成")
