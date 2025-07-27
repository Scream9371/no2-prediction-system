import datetime

from flask import Blueprint, jsonify

from config.cities import get_city_name, is_supported_city, get_all_cities
from database.crud import get_no2_records
from database.session import get_db
from ml.src.predict import predict_with_saved_model, visualize_predictions, export_predictions_to_csv
from ml.src.data_loader import load_data_from_mysql

# 中文城市名到英文城市名的映射（用于模型文件路径）
CHINESE_TO_ENGLISH_CITY_MAP = {
    "广州": "guangzhou",
    "深圳": "shenzhen", 
    "珠海": "zhuhai",
    "佛山": "foshan",
    "惠州": "huizhou",
    "东莞": "dongguan",
    "中山": "zhongshan",
    "江门": "jiangmen",
    "肇庆": "zhaoqing",
    "香港特别行政区": "hongkong",
    "澳门特别行政区": "macao"
}

def get_english_city_name(chinese_name: str) -> str:
    """
    将中文城市名转换为英文城市名（用于模型文件路径）
    
    Args:
        chinese_name (str): 中文城市名
        
    Returns:
        str: 英文城市名，如果找不到则返回原名称
        
    Example:
        >>> get_english_city_name("广州")
        'guangzhou'
        >>> get_english_city_name("未知城市") 
        '未知城市'
    """
    return CHINESE_TO_ENGLISH_CITY_MAP.get(chinese_name, chinese_name)


def web_predict_with_files(city: str, steps: int = 24):
    """
    Web API专用的预测函数，将预测结果保存到data/predictions目录
    
    Args:
        city (str): 城市名称
        steps (int): 预测步数
        
    Returns:
        pd.DataFrame: 预测结果
    """
    import os
    from datetime import datetime
    from config.paths import get_web_prediction_image_path, get_web_prediction_csv_path, ensure_directories
    
    # 确保目录存在
    ensure_directories()
    
    # 进行预测（Web API专用，仅使用训练管道模型）
    predictions = predict_with_saved_model(city, steps=steps, model_source='web')
    
    # 获取历史数据用于可视化
    history = load_data_from_mysql(city)
    
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 生成文件路径
    image_path = get_web_prediction_image_path(city, timestamp)
    csv_path = get_web_prediction_csv_path(city, timestamp)
    
    # 可视化并保存图像
    visualize_predictions(history, predictions, save_path=image_path)
    
    # 导出CSV数据
    export_predictions_to_csv(predictions, csv_path, city)
    
    print(f"Web预测文件已保存:")
    print(f"  图像: {image_path}")
    print(f"  CSV: {csv_path}")
    
    return predictions

api_bp = Blueprint("api", __name__)

@api_bp.route("/api/no2/<city_id>")
def get_no2(city_id):
    """
    获取指定城市的历史NO₂浓度数据
    
    Args:
        city_id (str): 城市ID，从URL路径中获取
        
    Returns:
        JSON: 历史NO₂数据列表，每条记录包含：
            - observation_time: 观测时间 (ISO格式字符串)
            - no2_concentration: NO₂浓度 (μg/m³)
            - temperature: 气温 (摄氏度)
            - humidity: 相对湿度 (百分比)
            - wind_speed: 风速 (公里/小时)
            - wind_direction: 风向 (360角度)
            - pressure: 大气压 (百帕)
            
    HTTP状态码:
        200: 成功返回数据
        400: 无效的城市ID
        500: 服务器内部错误
        
    示例:
        GET /api/no2/101280800
        返回: [{"observation_time": "2025-07-25T00:00:00", "no2_concentration": 25.6, ...}, ...]
    """
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

@api_bp.route("/api/predict/no2/<city_id>")
def predict_no2(city_id):
    """
    获取指定城市未来24小时的NO₂浓度预测数据
    
    这是核心预测API，使用训练好的NC-CQR模型预测城市未来48小时的NO₂浓度及95%置信区间。
    
    Args:
        city_id (str): 城市ID，从URL路径中获取
        
    Returns:
        JSON: 预测数据，包含以下字段：
            - updateTime (str): 更新时间，格式 "YYYY-MM-DD HH:MM"
            - currentValue (float): 当前预测值 (μg/m³)
            - avgValue (float): 24小时平均预测值 (μg/m³)
            - times (list): 24个时间点，格式 ["HH:MM", ...]，基于实际预测时间
            - values (list): 24个预测值 (μg/m³)
            - low (list): 置信区间下限值 (μg/m³)
            - high (list): 置信区间上限值 (μg/m³)
            - warning (str, 可选): 当模型不存在时的警告信息
            
    模型选择策略:
        1. 仅使用训练管道的最新模型 (ml/models/latest/)
        2. 模型不存在时返回示例数据并显示警告
        
    HTTP状态码:
        200: 成功返回预测数据
        400: 不支持的城市ID
        500: 预测过程出错
        
    示例:
        GET /api/predict/no2/101280800
        返回: {
            "updateTime": "2025-07-25 12:00",
            "currentValue": 25.6,
            "avgValue": 23.4,
            "times": ["00:00", "01:00", ..., "23:00"],
            "values": [25.6, 24.3, ..., 26.8],
            "low": [19.2, 18.1, ..., 20.4],
            "high": [32.0, 30.5, ..., 33.2]
        }
    """
    if not is_supported_city(city_id):
        return jsonify({"error": "不支持的城市"}), 400
    try:
        # 获取城市名称用于预测
        city_name = get_city_name(city_id)
        # 转换为英文城市名（用于模型文件路径）
        english_city_name = get_english_city_name(city_name)
        
        # 检查模型是否存在（优先使用训练管道模型）
        import os
        from config.paths import get_latest_model_path, get_control_model_path
        
        # 先尝试训练管道的最新模型
        model_path = get_latest_model_path(english_city_name)
        if not os.path.exists(model_path):
            # 如果训练管道模型不存在，尝试控制脚本模型
            model_path = get_control_model_path(english_city_name)
        
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
        
        # 使用自定义的Web预测函数，保存文件到data/predictions目录
        predictions_df = web_predict_with_files(city=english_city_name, steps=24)

        # 将DataFrame转换为前端需要的JSON格式
        if predictions_df is not None and hasattr(predictions_df, 'empty') and not predictions_df.empty:
            # 从预测数据中提取实际的时间标签
            import pandas as pd
            times = [pd.to_datetime(t).strftime("%H:%M") for t in predictions_df['observation_time'].tolist()[:24]]
            
            # 提取预测数据
            values = predictions_df['prediction'].tolist()[:24]
            low = predictions_df['lower_bound'].tolist()[:24]
            high = predictions_df['upper_bound'].tolist()[:24]
            
            current_value = values[0] if values else 0
            avg_value = sum(values) / len(values) if values else 0
            
            # 获取当前时间作为更新时间
            import datetime
            current_time = datetime.datetime.now()
            
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

@api_bp.route("/api/cities")
def get_cities():
    """
    获取所有支持的城市列表
    
    返回大湾区所有支持预测的城市信息，包括城市ID和中文名称。
    前端使用此接口获取城市映射关系，用于城市搜索和ID转换。
    
    Returns:
        JSON: 城市信息列表，每个城市包含：
            - id (str): 城市ID，用于其他API调用
            - name (str): 城市中文名称
            
    HTTP状态码:
        200: 成功返回城市列表
        
    示例:
        GET /api/cities
        返回: [
            {"id": "101280101", "name": "广州"},
            {"id": "101280601", "name": "深圳"},
            {"id": "101280800", "name": "佛山"},
            ...
        ]
        
    支持的城市:
        广州、深圳、珠海、佛山、惠州、东莞、中山、江门、肇庆、香港特别行政区、澳门特别行政区
    """
    return jsonify(get_all_cities())
