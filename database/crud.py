from sqlalchemy.orm import Session
from .models import NO2Record


def create_no2_record(db: Session, record_data: dict):
    record = NO2Record(**record_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_no2_records(db: Session, city_id: str, limit: int = 100):
    return (
        db.query(NO2Record)
        .filter(NO2Record.city_id == city_id)
        .order_by(NO2Record.datetime.desc())
        .limit(limit)
        .all()
    )
