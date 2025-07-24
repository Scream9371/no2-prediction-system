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
    
    try:
        db_gen = get_db()
        db = next(db_gen)
        # 修复：使用城市名称而非城市ID
        records = get_no2_records(db, city_name)
        db.close()
        
        # 转换记录为字典列表
        result = []
        for record in records:
            record_dict = {}
            for column in record.__table__.columns:
                value = getattr(record, column.name)
                # 处理datetime对象
                if isinstance(value, datetime.datetime):
                    record_dict[column.name] = value.isoformat()
                else:
                    record_dict[column.name] = value
            result.append(record_dict)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"获取历史数据失败: {str(e)}"}), 500

# 预测接口
@api_bp.route("/api/predict/no2/<city_id>")
def predict_no2(city_id):
    if not is_supported_city(city_id):
        return jsonify({"error": "不支持的城市"}), 400
    try:
        # 获取城市名称用于预测
        city_name = get_city_name(city_id)
        
        # 检查模型是否存在（优先使用训练管道模型）
        import os
        from config.paths import get_latest_model_path, get_control_model_path
        
        # 先尝试训练管道的最新模型
        model_path = get_latest_model_path(city_name)
        if not os.path.exists(model_path):
            # 如果训练管道模型不存在，尝试控制脚本模型
            model_path = get_control_model_path(city_name)
        
        if not os.path.exists(model_path):
            # 如果模型不存在，返回示例数据并提示用户
            import datetime
            current_time = datetime.datetime.now()
            times = [(current_time + datetime.timedelta(hours=i)).strftime("%H:%M") for i in range(24)]
            
            # 生成示例预测数据
            import random
            base_value = random.uniform(30, 80)
            values = [round(base_value + random.uniform(-5, 5), 1) for _ in range(24)]
            low = [round(v - 10, 1) for v in values]
            high = [round(v + 10, 1) for v in values]
            
            return jsonify({
                "updateTime": current_time.strftime("%Y-%m-%d %H:%M"),
                "currentValue": values[0],
                "avgValue": round(sum(values) / len(values), 1),
                "times": times,
                "values": values,
                "low": low,
                "high": high,
                "warning": f"模型文件不存在 ({model_path})，显示的是示例数据。请先训练模型。"
            })
        
        predictions_df = predict_mode(city=city_name, steps=24)
        
        # 将DataFrame转换为前端需要的JSON格式
        if predictions_df is not None and hasattr(predictions_df, 'empty') and not predictions_df.empty:
            # 生成时间标签（未来24小时）
            import datetime
            current_time = datetime.datetime.now()
            times = [(current_time + datetime.timedelta(hours=i)).strftime("%H:%M") for i in range(24)]
            
            # 提取预测数据
            values = predictions_df['prediction'].tolist()[:24]
            low = predictions_df['lower_bound'].tolist()[:24]
            high = predictions_df['upper_bound'].tolist()[:24]
            
            current_value = values[0] if values else 0
            avg_value = sum(values) / len(values) if values else 0
            
            return jsonify({
                "updateTime": current_time.strftime("%Y-%m-%d %H:%M"),
                "currentValue": round(current_value, 1),
                "avgValue": round(avg_value, 1),
                "times": times,
                "values": [round(v, 1) for v in values],
                "low": [round(l, 1) for l in low],
                "high": [round(h, 1) for h in high]
            })
        else:
            return jsonify({"error": "无法获取预测数据，请检查模型和数据"}), 500
            
    except Exception as e:
        return jsonify({"error": f"预测失败: {str(e)}"}), 500

# 城市列表接口
@api_bp.route("/api/cities")
def get_cities():
    return jsonify(get_all_cities())
