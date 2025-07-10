from ml.src.evaluate import evaluate_model
from ml.src.retrain import auto_retrain
from database.session import get_db
from config.settings import settings

CITY_LIST = ["广州", "深圳", "珠海", "佛山", "惠州", "东莞", "中山", "江门", "肇庆"]


def monitor_and_retrain():
    db_gen = get_db()
    db = next(db_gen)
    for city in CITY_LIST:
        # 这里假设有测试集X_test, y_test的获取方式
        # X_test, y_test = ...
        # if auto_retrain(db, city, X_test, y_test):
        #     print(f"模型已为{city}自动重训")
        pass
    db.close()
