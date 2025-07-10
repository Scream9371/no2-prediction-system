from flask import Blueprint, jsonify, request
from database.session import get_db
from database.crud import get_no2_records

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/no2/<city_id>")
def get_no2(city_id):
    db_gen = get_db()
    db = next(db_gen)
    records = get_no2_records(db, city_id)
    db.close()
    return jsonify([r.__dict__ for r in records])
