from ml.src.train import train_model
from database.session import get_db

CITY_LIST = ["广州", "深圳", "珠海", "佛山", "惠州", "东莞", "中山", "江门", "肇庆"]

if __name__ == "__main__":
    db_gen = get_db()
    db = next(db_gen)
    for city in CITY_LIST:
        train_model(db, city)
        print(f"{city}模型训练完成")
    db.close()
