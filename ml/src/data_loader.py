import pandas as pd
from sqlalchemy.orm import Session
from database.models import NO2Record


def load_data_from_db(db: Session, city_id: str, days: int = 10):
    records = (
        db.query(NO2Record)
        .filter(NO2Record.city_id == city_id)
        .order_by(NO2Record.datetime.desc())
        .limit(days * 24)
        .all()
    )
    data = [r.__dict__ for r in records]
    df = pd.DataFrame(data)
    return df
