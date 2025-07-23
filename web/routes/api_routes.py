import datetime
from flask import Blueprint, jsonify, request
from database.session import get_db
from database.crud import get_no2_records

# 导入需要的模块（如预测、评估逻辑）
from ml.src.control import predict_mode, evaluate_mode, get_supported_cities

# 导入城市配置模块
from config.cities import get_city_name, is_supported_city, get_all_cities

api_bp = Blueprint("api", __name__)

@api_bp.route("/api/no2/<city_id>")
def get_no2(city_id):
    # 转换城市ID为名称
    city_name = get_city_name(city_id)
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
    if not is_supported_city(city_id):
        return jsonify({"error": "不支持的城市"}), 400
    try:
        prediction = predict_mode(city=city_id, steps=24)
        return jsonify(prediction)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 城市列表接口
@api_bp.route("/api/cities")
def get_cities():
    return jsonify(get_all_cities())

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