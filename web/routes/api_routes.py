import datetime
from flask import Blueprint, jsonify, request
from database.session import get_db
from database.crud import get_no2_records

# 导入需要的模块（如预测、评估逻辑）
from ml.src.control import predict_mode, evaluate_mode, get_supported_cities


api_bp = Blueprint("api", __name__)

# 城市ID到名称的映射表（与get_cities接口保持一致）
CITY_ID_TO_NAME = {
    "101280101": "广州",
    "101280601": "深圳",
    "101280701": "珠海",
    "101280800": "佛山",
    "101280301": "惠州",
    "101281601": "东莞",
    "101281701": "中山",
    "101281101": "江门",
    "101280901": "肇庆",
    "101320101": "香港特别行政区",  
    "101330101": "澳门特别行政区"   
}

@api_bp.route("/api/no2/<city_id>")
def get_no2(city_id):
    #  转换城市ID为名称
    city_name = CITY_ID_TO_NAME.get(city_id)
    if not city_name:
        return jsonify({"error": "无效的城市ID"}), 400  # 处理无效ID
    db_gen = get_db()
    db = next(db_gen)
    records = get_no2_records(db, city_id)
    db.close()
    return jsonify([r.__dict__ for r in records])

# 预测接口
@api_bp.route("/api/predict/no2/<city_id>")
def predict_no2(city_id):
    if city_id not in get_supported_cities():
        return jsonify({"error": "不支持的城市"}), 400
    try:
        prediction = predict_mode(city=city_id, steps=24)
        return jsonify(prediction)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 城市列表接口
@api_bp.route("/api/cities")
def get_cities():
    cities = [
    {"id": "101280101", "name": "广州"},
    {"id": "101280601", "name": "深圳"},
    {"id": "101280701", "name": "珠海"},
    {"id": "101280800", "name": "佛山"},
    {"id": "101280301", "name": "惠州"},
    {"id": "101281601", "name": "东莞"},
    {"id": "101281701", "name": "中山"},
    {"id": "101281101", "name": "江门"},
    {"id": "101280901", "name": "肇庆"},
    {"id": "101320101", "name": "香港特别行政区"},
    {"id": "101330101", "name": "澳门特别行政区"}
]

# NO2数据接口
@api_bp.route("/api/no2")
def get_no2_data():
    city_id = request.args.get('cityId')
    if not city_id:
        return jsonify({"error": "缺少cityId参数"}), 400
    
    # 此处应从数据库或模型获取真实数据，以下为示例
    # 实际应用中需替换为真实数据查询逻辑
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return jsonify({
        "updateTime": current_time,
        "currentValue": 56,  # 示例值
        "avgValue": 52,      # 示例值
        "times": ["00:00", "01:00", "02:00"],  # 未来24小时时间
        "values": [56, 58, 55],                # 预测值
        "low": [50, 52, 49],                   # 下限
        "high": [62, 64, 61]                   # 上限
    })

    return jsonify(cities)